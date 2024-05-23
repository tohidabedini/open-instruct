import random
import json
import re
import argparse
import time
import os
from collections import Counter
from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

random.seed(42)

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'data', 'evaluation.db')
print(app.config['SQLALCHEMY_DATABASE_URI'])
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# GLOBAL VARIABLE for the comparison instances
COMPARISON_INSTANCES=[]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    approved = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

class EvaluationRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instance_index = db.Column(db.Integer)
    instance_id = db.Column(db.String(200))
    prompt = db.Column(db.String(1e4))
    model_a = db.Column(db.String(200))
    model_b = db.Column(db.String(200))
    completion_a = db.Column(db.String(1e4))
    completion_b = db.Column(db.String(1e4))
    completion_a_is_acceptable = db.Column(db.String(50))
    completion_b_is_acceptable = db.Column(db.String(50))
    preference = db.Column(db.String(50))
    instance_quality = db.Column(db.String(50))
    comment = db.Column(db.String(1e4))
    evaluator = db.Column(db.String(100))
    timestamp = db.Column(db.String(100))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            if user.approved:
                login_user(user)
                return redirect(url_for('index'))
            else:
                return 'اکانت شما تأیید نشده است.'
        else:
            return 'نام کاربری یا رمز عبور وارد شده نامعتبر است.'
    else:
        return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, approved=False)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    else:
        return render_template('login.html')


@app.route('/admin/approve_users', methods=['GET', 'POST'])
@login_required
def approve_users():
    if not current_user.is_admin:
        return 'شما مجوز مشاهده این صفحه را ندارید.'

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        user = User.query.get(user_id)
        user.approved = True
        db.session.commit()
        return redirect(url_for('approve_users'))

    unapproved_users = User.query.filter_by(approved=False).all()
    return render_template('approve_users.html', users=unapproved_users)


@app.route('/admin/list_users', methods=['GET', 'POST'])
@login_required
def list_users():
    if not current_user.is_admin:
        return 'شما مجوز مشاهده این صفحه را ندارید.'

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        user = User.query.get(user_id)
        user.approved = False
        db.session.commit()
        return redirect(url_for('list_users'))

    approved_users = User.query.filter_by(approved=True).all()
    return render_template('list_users.html', users=approved_users)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
    

@app.route('/')
def index():
    # check if the user is logged in
    if current_user.is_authenticated:
        context = {
            'index': 0,
            'current_user': current_user,
            'count_left_indices': 0,
            'count_all_indices': 0,
        }

        return redirect(url_for('instances', **context))
    else:
        return redirect(url_for('login'))


@app.route("/api/instances-status", methods=["GET"])
@login_required
def get_instances_status():
    indices, int_indices = get_all_ids_from_instances(COMPARISON_INSTANCES)
    left_indices = get_instance_index_difference(current_user.username, int_indices)
    count_left_indices = len(left_indices)
    count_all_indices = len(int_indices)

    return jsonify({"count_left_indices": count_left_indices,
                    "count_all_indices": count_all_indices,
                    }), 200


@app.route("/left-instances")
@login_required
def get_left_instances():
    indices, int_indices = get_all_ids_from_instances(COMPARISON_INSTANCES)
    left_indices = get_instance_index_difference(current_user.username, int_indices)
    count_left_indices = len(left_indices)
    count_all_indices = len(int_indices)

    context = {
        'current_user': current_user,
        'left_indices': left_indices,
        'count_left_indices': count_left_indices,
        'count_all_indices': count_all_indices
    }
    return render_template('left_instances.html', **context)


@app.route('/instances/<int:index>')
def instances(index):
    context = {
        'index': index,
        'current_user': current_user,
        'count_left_indices': 0,
        'count_all_indices': 0,
    }
    return render_template('index.html', **context)


@app.route("/api/model-outputs/<int:index>", methods=["GET"])
def get_model_outputs(index):
    if 0 <= index < len(COMPARISON_INSTANCES):
        prompt = COMPARISON_INSTANCES[index]["prompt"]
        completions = COMPARISON_INSTANCES[index]["completions"]
        random.shuffle(completions)
        return jsonify({"prompt": prompt, "completions": completions}), 200
    return jsonify({"error": "Index out of range"}), 200


@app.route("/summary", methods=["GET"])
@login_required
def summary():
    results = summarize_results()
    return jsonify(results), 200


def get_all_ids_from_instances(instances_list):
    ids = []
    int_ids = []
    for i in range(len(instances_list)):
        ids.append(instances_list[i]["id"])
        int_ids.append(i)
    return set(ids), set(int_ids)


def get_instance_index_difference(evaluator, int_indices):
    existing_indices = db.session.query(EvaluationRecord.instance_index).filter_by(evaluator=evaluator).all()
    existing_indices = [record.instance_index for record in existing_indices]

    difference = set(int_indices) - set(existing_indices)

    return sorted(list(difference))


def count_user_contributions(users, records):

    all_instances_count = len(COMPARISON_INSTANCES)
    indices, int_indices = get_all_ids_from_instances(COMPARISON_INSTANCES)

    # print(len(COMPARISON_INSTANCES))
    # print(COMPARISON_INSTANCES[0])
    # print(records[0].instance_index)

    user_contributions = {}
    for user in users:
        user_contributions[user.username] = {"count_done": 0, "count_left": 0, "left_instances": [], "done_instances": [], }
    for record in records:
        user_contributions[record.evaluator]["count_done"] += 1
        user_contributions[record.evaluator]["done_instances"].append(record.instance_index)

    for user in users:
        user_contributions[user.username]["count_left"] = all_instances_count - user_contributions[user.username]["count_done"]
        # user_contributions[user.username]["left_instances"] = sorted(list(int_indices.difference(set(user_contributions[user.username]["done_instances"]))))
        user_contributions[user.username]["left_instances"] = get_instance_index_difference(user.username, int_indices)

    user_contributions["all"] = len(records)

    return user_contributions


def get_progress(records, users):
    completed_instance_indices = set([record.instance_index for record in records])
    missing_instances = []
    for index in range(len(COMPARISON_INSTANCES)):
        if index not in completed_instance_indices:
            missing_instances.append(index)
    return {
        "completed_at_least_by_one_of_annotators": len(completed_instance_indices),
        "total": len(COMPARISON_INSTANCES),
        "missing_indices": missing_instances,
    }


def get_acceptance_results(records, target_model_a, target_model_b):
    acceptance_results = {
        target_model_a: {},
        target_model_b: {},
    }
    for record in records:
        instance_id = record.instance_id
        if instance_id not in acceptance_results[record.model_a]:
            acceptance_results[record.model_a][instance_id] = []
        acceptance_results[record.model_a][instance_id].append(record.completion_a_is_acceptable)
        
        if instance_id not in acceptance_results[record.model_b]:
            acceptance_results[record.model_b][instance_id] = []
        acceptance_results[record.model_b][instance_id].append(record.completion_b_is_acceptable)

    # count how many instances get multiple annotations
    instances_with_multiple_annotations = [instance_id for instance_id, results in acceptance_results[record.model_a].items() if len(results) > 1]
    agreement_results = {
        "num_instances_with_multiple_annotations": len(instances_with_multiple_annotations),
        "acceptance_agreement": None,
    }
    assert target_model_a in acceptance_results
    assert target_model_b in acceptance_results
    # get agreement on acceptance
    if len(instances_with_multiple_annotations) > 0:
        agreed_model_a_acceptance = 0
        agreed_model_b_acceptance = 0
        for instance_id in instances_with_multiple_annotations:
            if len(set(acceptance_results[target_model_a][instance_id][-2:])) == 1:
                agreed_model_a_acceptance += 1
            if len(set(acceptance_results[target_model_b][instance_id][-2:])) == 1:
                agreed_model_b_acceptance += 1
        agreement_results["acceptance_agreement"] = \
            (agreed_model_a_acceptance + agreed_model_b_acceptance) / (2 * len(instances_with_multiple_annotations))
        agreement_results[f"{target_model_a}_acceptance_agreement"] = agreed_model_a_acceptance / len(instances_with_multiple_annotations)
        agreement_results[f"{target_model_b}_acceptance_agreement"] = agreed_model_b_acceptance / len(instances_with_multiple_annotations)

    return {
        f"{target_model_a}": sum([1 if x[-1]=="yes" else 0 for _, x in acceptance_results[target_model_a].items()]) / len(acceptance_results[target_model_a]),
        f"{target_model_b}": sum([1 if x[-1]=="yes" else 0 for _, x in acceptance_results[target_model_b].items()]) / len(acceptance_results[target_model_b]),
        "agreement": agreement_results,
    }


def get_comparison_results(records, target_model_a, target_model_b):
    comparison_results = {}
    for record in records:
        instance_id = record.instance_id
        model_a = record.model_a
        model_b = record.model_b
        if instance_id not in comparison_results:
            comparison_results[instance_id] = []

        if record.preference == "a-is-better":
            comparison_results[instance_id].append(f"{model_a} is clearly better")
        elif record.preference == "a-is-slightly-better":
            comparison_results[instance_id].append(f"{model_a} is slightly better")
        elif record.preference == "b-is-better":
            comparison_results[instance_id].append(f"{model_b} is clearly better")
        elif record.preference == "b-is-slightly-better":
            comparison_results[instance_id].append(f"{model_b} is slightly better")
        elif record.preference == "tie":
            comparison_results[instance_id].append("tie")
        else:
            print("-------------------------------------")
            print("Unknown preference value.")
            print(record)

    # thre can be multiple annotations for each instance; use the latest comparison result for each instance
    # latest_comparison_results = [results[-1] for _, results in comparison_results.items()]
    latest_comparison_results = []
    for _, results in comparison_results.items():
        for result in results:
            latest_comparison_results.append(result)

    model_wins_counter = Counter(latest_comparison_results)
    model_wins_rates = {
        result: count / len(latest_comparison_results) for result, count in model_wins_counter.items()
    }
    # merge the clearly better and slightly better results
    model_wins_rates[f"{target_model_a}_wins"] = \
        sum([v for k, v in model_wins_rates.items() if target_model_a in k])
    model_wins_rates[f"{target_model_b}_wins"] = \
        sum([v for k, v in model_wins_rates.items() if target_model_b in k])
    
    # count how many instances get multiple annotations
    instances_with_multiple_annotations = [instance_id for instance_id, results in comparison_results.items() if len(results) > 1]
    agreement_results = {
        "num_instances_with_multiple_annotations": len(instances_with_multiple_annotations),
        "comparison_agreement": None,
        "relexed_comparison_agreement": None,
    }
    if instances_with_multiple_annotations:
        agreed_comparison = 0
        relexed_agreed_comparison = 0
        for instance_id in instances_with_multiple_annotations:
            simplified_comparisons = []
            for comparison_result in comparison_results[instance_id]:
                if comparison_result == "tie":
                    simplified_comparisons.append("tie")
                elif target_model_a in comparison_result:
                    simplified_comparisons.append(target_model_a)
                elif target_model_b in comparison_result:
                    simplified_comparisons.append(target_model_b)
                else:
                    print("Unknown comparison result.")
                    print(comparison_result)
            if len(set(simplified_comparisons[-2:])) == 1:
                agreed_comparison += 1
                relexed_agreed_comparison += 1
            else:
                if "tie" in simplified_comparisons[-2:]:
                    relexed_agreed_comparison += 0.5
        agreement_results["comparison_agreement"] = agreed_comparison / len(instances_with_multiple_annotations) 
        agreement_results["relexed_comparison_agreement"] = relexed_agreed_comparison / len(instances_with_multiple_annotations)   
    
    model_wins_rates["agreement"] = agreement_results
    return model_wins_rates


def summarize_results():
    results = {}
    users = User.query.all()
    records = EvaluationRecord.query.all()

    # get the number of completed instances for all and each user
    results["user_contributions"] = count_user_contributions(users, records)

    # get the missing instances
    results["progress"] = get_progress(records, users)
    
    # get the comparison model pairs
    model_pairs = set([tuple(sorted([record.model_a, record.model_b])) for record in records])
    results["model_pairs"] = list(model_pairs)
    
    results["results"] = {}
    for target_model_a, target_model_b in model_pairs:
        feedback_records = {}
        comparison_records = []
        for record in records:
            # instance id is used to identify the comparison instance
            # there could be multiple records for the same instance
            instance_id = record.instance_id

            # skip if the record is not for the target model pair
            if set([target_model_a, target_model_b]) != set([record.model_a, record.model_b]):
                assert any([set([record.model_a, record.model_b]) == set(pair) for pair in model_pairs])
                continue
            
            # skip if the record is a feedback
            if record.instance_quality:
                if record.instance_quality not in feedback_records:
                    feedback_records[record.instance_quality] = []
                feedback_records[record.instance_quality].append(record.instance_index)
                # continue

            comparison_records.append(record)

        acceptance_results = get_acceptance_results(comparison_records, target_model_a, target_model_b)
        comparison_results = get_comparison_results(comparison_records, target_model_a, target_model_b)
        results["results"][f"{target_model_a}_vs_{target_model_b}"] = {
            "acceptance_results": acceptance_results,
            "comparison_results": comparison_results,
            "feedback_records": feedback_records,
        }        
    return results
    

@app.route("/api/submit-evaluation", methods=["POST"])
@login_required
def submit_evaluation():
    evaluation_data = request.get_json()
    print("Got new evaluation data:")
    print(evaluation_data)

    # Check for existing record with the same instance_index and evaluator
    existing_record = EvaluationRecord.query.filter_by(
        instance_index=evaluation_data["index"],
        evaluator=evaluation_data["evaluator"]
    ).first()

    if existing_record:
        existing_record.instance_id = COMPARISON_INSTANCES[evaluation_data["index"]]["id"]
        existing_record.prompt = evaluation_data["prompt"]
        existing_record.model_a = evaluation_data["model_a"]
        existing_record.model_b = evaluation_data["model_b"]
        existing_record.completion_a = evaluation_data["completion_a"]
        existing_record.completion_b = evaluation_data["completion_b"]
        existing_record.completion_a_is_acceptable = evaluation_data["completion_a_is_acceptable"]
        existing_record.completion_b_is_acceptable = evaluation_data["completion_b_is_acceptable"]
        existing_record.preference = evaluation_data["preference"]
        existing_record.timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    else:
        new_record = EvaluationRecord(
            instance_index=evaluation_data["index"],
            instance_id=COMPARISON_INSTANCES[evaluation_data["index"]]["id"],
            prompt=evaluation_data["prompt"],
            model_a=evaluation_data["model_a"],
            model_b=evaluation_data["model_b"],
            completion_a=evaluation_data["completion_a"],
            completion_b=evaluation_data["completion_b"],
            completion_a_is_acceptable=evaluation_data["completion_a_is_acceptable"],
            completion_b_is_acceptable=evaluation_data["completion_b_is_acceptable"],
            preference=evaluation_data["preference"],
            evaluator=evaluation_data["evaluator"],
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        )
        db.session.add(new_record)

    db.session.commit()
    return jsonify({"message": "Evaluation data submitted successfully"}), 200


@app.route("/api/submit-feedback", methods=["POST"])
@login_required
def submit_feedback():
    feedback_data = request.get_json()
    print("Got new feedback:")
    print(feedback_data)

    # Check for existing record with the same instance_index and evaluator
    existing_record = EvaluationRecord.query.filter_by(
        instance_index=feedback_data["index"],
        evaluator=feedback_data["evaluator"]
    ).first()

    # If an existing record is found, update it
    if existing_record:
        existing_record.instance_id = COMPARISON_INSTANCES[feedback_data["index"]]["id"]
        existing_record.prompt = feedback_data["prompt"]
        existing_record.model_a = feedback_data["model_a"]
        existing_record.model_b = feedback_data["model_b"]
        existing_record.completion_a = feedback_data["completion_a"]
        existing_record.completion_b = feedback_data["completion_b"]
        existing_record.instance_quality = feedback_data["instance_quality"]
        existing_record.comment = feedback_data["comment"] if (feedback_data["comment"] != "") else existing_record.comment
        existing_record.timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    else:
        # Create a new record if no existing record is found
        new_record = EvaluationRecord(
            instance_index=feedback_data["index"],
            instance_id=COMPARISON_INSTANCES[feedback_data["index"]]["id"],
            prompt=feedback_data["prompt"],
            model_a=feedback_data["model_a"],
            model_b=feedback_data["model_b"],
            completion_a=feedback_data["completion_a"],
            completion_b=feedback_data["completion_b"],
            instance_quality=feedback_data["instance_quality"],
            comment=feedback_data["comment"],
            evaluator=feedback_data["evaluator"],
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        )
        db.session.add(new_record)

    db.session.commit()
    return jsonify({"message": "Feedback submitted successfully"}), 200

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--comparison_data_path",
        type=str,
        required=True,
        help="The path to the data file containing the instances to be evaluated. "
             "Each instance should have a prompt and two completions."
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="The host of the server."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5001,
        help="The port of the server."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Whether to run the server in debug mode."
    )
    args = parser.parse_args()

    if not os.path.exists(os.path.join(os.getcwd(), 'data', 'evaluation.db')):
        with app.app_context():
            db.create_all()
            new_user = User(username="admin", password=generate_password_hash(os.getenv("ADMIN_PASS")), approved=True, is_admin=True)
            db.session.add(new_user)
            db.session.commit()

    # load the predictions
    global COMPARISON_INSTANCES
    with open(args.comparison_data_path, "r") as f:
        COMPARISON_INSTANCES = [json.loads(line.strip()) for line in f.readlines()]

    print("Total number of comparison instances: {}".format(len(COMPARISON_INSTANCES)))

    # run the app and listen on port 5000
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
