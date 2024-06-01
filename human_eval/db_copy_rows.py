import sqlite3

def duplicate_rows(db_path, new_evaluators):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to get all rows with evaluator="test"
    cursor.execute("SELECT instance_index, instance_id, prompt, model_a, model_b, completion_a, completion_b, "
                   "completion_a_is_acceptable, completion_b_is_acceptable, preference, instance_quality, comment, "
                   "evaluator, timestamp FROM evaluation_record WHERE evaluator = ?", ("test",))
    rows = cursor.fetchall()

    print(len(rows))

    # Insert the duplicated rows with new evaluators
    for evaluator in new_evaluators:
        for row in rows:
            # Unpack the row and add the new evaluator
            (instance_index, instance_id, prompt, model_a, model_b, completion_a, completion_b,
             completion_a_is_acceptable, completion_b_is_acceptable, preference, instance_quality,
             comment, _, timestamp) = row

            cursor.execute("INSERT INTO evaluation_record (instance_index, instance_id, prompt, model_a, model_b, completion_a, "
                           "completion_b, completion_a_is_acceptable, completion_b_is_acceptable, preference, "
                           "instance_quality, comment, evaluator, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (instance_index, instance_id, prompt, model_a, model_b, completion_a, completion_b,
                            completion_a_is_acceptable, completion_b_is_acceptable, preference, instance_quality,
                            comment, evaluator, timestamp))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

# Example usage
db_path = "./data/evaluation.db"
new_evaluators = ["aalizadeh", "farzaneh", "izadi", "tayyebi"]
duplicate_rows(db_path, new_evaluators)

