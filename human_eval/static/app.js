// Global variable to store the current index
let current_index = instance_index;

// Fetch the initial model outputs based on the instance index
rendere_instance(current_index);

// Fetch the model outputs from the API and update the UI
async function rendere_instance(index) {
    const response = await fetch(`/api/model-outputs/${index}`);
    const response_count = await fetch(`/api/instances-status`);
    const data = await response.json();
    const count_data = await response_count.json();

    // if the response is error, show the out of range message
    if (data.error == "Index out of range") {
        show_alert(
            "شما یک نمونه خارج از محدوده درخواست کردید. شما ممکن است تمام ارزیابی ها را تکمیل کرده باشید. از همکاری شما سپاسگذاریم!",
            "danger",
            insert_after_selector="#instance-info",
            timeout=1e10 // set timeout to a very large number so that the alert doesn't disappear
        );
        clear_all();
        return;
    }

    clear_all();
    $("#instance-id").html(`نمونه شماره ${index}`);

    // let's use a unified format here that support multiple messages, though currently we only have one user prompt.
    var messages = [{"role": "user", "text": data.prompt}];
    var history_message_region = $("#history-message-region");
    history_message_region.empty();

    var count_instances_region = $("#count-instances-region");
    count_instances_region.empty();


$.each(messages, function(i, message) {
    var icon = message.role == "user" ? "🧑" : "🤖";
    var definition = message.role == "user" ? "ورودی/سوال داده شده به مدل:" : "پاسخ مدل:";

    var $icon_and_definition = $("<div></div>").addClass("row").html(`
        <div class="col icon-col">
            <button class="role-icon">${icon}</button>
        </div>
        <div class="col message-col">
            <h5>${definition}</h5>
        </div>
    `);

    var $message_text = $("<div></div>").addClass("row").html(`
        <div class="col message-col history-message-col">
            <xmp class="message-text">${message.text}</xmp>
        </div>
    `);

    history_message_region.append($icon_and_definition).append($message_text);
});

    // now render the completions
    completion_a = data.completions[0];
    completion_b = data.completions[1];
    
    $("#completion-A-col").html(`
        <xmp class="message-text" id="${completion_a.model}-completion">${completion_a.completion}</xmp>
    `);
    $("#completion-B-col").html(`
        <xmp class="message-text" id="${completion_b.model}-completion">${completion_b.completion}</xmp>
    `);

    count_instances_region.html(`
        تعداد ${count_data.count_left_indices} نمونه انجام نشده از ${count_data.count_all_indices} نمونه دارید.
    `);

    // Change the URL path with the current index
    window.history.pushState(null, '', `/instances/${index}`);
}


// clear everything
function clear_all() {
    $('#history-message-region').html(`
        <div class="row">
            <div class="col icon-col">
                <button class="role-icon">🧑</button>
            </div>
            <div class="col message-col">
                <h5>ورودی/سوال داده شده به مدل:</h5>
            </div>
        </div>
        <div class="row">
            <div class="col message-col history-message-col">
                <xmp class="message-text"></xmp>
            </div>
        </div>
    `);
    $('.completion-col').empty(); 
    $('input[type="checkbox"], input[type="radio"]').prop('checked', false);
    $('textarea').val('');
}


function show_alert(message, type, insert_after_selector, timeout=5000) {
    const alert_container = $(`<div class="alert alert-${type} mx-auto mt-2" style="max-width:500px" role="alert">${message}</div>`)[0];
    $(insert_after_selector)[0].insertAdjacentElement("afterend", alert_container);
    setTimeout(() => {
        alert_container.remove();
    }, timeout);
}

async function submit_evaluation() {
    try {
        // get the model name by trimming out the last `-completion` part
        const model_a = $("#completion-A-col").find("xmp").attr("id").slice(0, -11);
        const model_b = $("#completion-B-col").find("xmp").attr("id").slice(0, -11);
        const completion_a_is_acceptable = $("input[name='a-is-acceptable']:checked").val();
        const completion_b_is_acceptable = $("input[name='b-is-acceptable']:checked").val();
        const preference = $("input[name='preference-selection']:checked").val();
        
        // get the prompt and completions
        const prompt = $("#history-message-region").find("xmp").text();
        const completion_a = $("#completion-A-col").find("xmp").text();
        const completion_b = $("#completion-B-col").find("xmp").text();

        // make sure all the required fields are filled
        if (completion_a_is_acceptable == undefined || completion_b_is_acceptable == undefined || preference == undefined) {
            show_alert("لطفا تمامی سوال ها را پاسخ دهید.", "danger", insert_after_selector="#evaluation-submit", timeout=5000);
            return;
        }
        const response = await fetch("/api/submit-evaluation", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                index: current_index,
                model_a,
                model_b,
                prompt,
                completion_a,
                completion_b,
                completion_a_is_acceptable,
                completion_b_is_acceptable,
                preference,
                evaluator: username 
            }),
        });
        
        // if the response is 200, show the success message
        if (response.status == 200) {
            show_alert("ارزیابی با موفقیت ثبت شد.", "success", insert_after_selector="#evaluation-submit", timeoutput=5000);
            console.log("ارزیابی با موفقیت ثبت شد.");
            current_index++;
            rendere_instance(current_index);
        }
        else if (response.status == 401) {
            show_alert("برای ثبت ارزیابی باید وارد شوید.", "danger", insert_after_selector="#evaluation-submit", timeoutput=5000);
        }
        else {
            console.log(response);
            show_alert("خطا در هنگام ثبت ارزیابی. لطفا دوباره تلاش کنید.", "danger", insert_after_selector="#evaluation-submit", timeoutput=5000);
            console.error("خطا در هنگام ثبت ارزیابی:", response.status);
        }
    } catch (error) {
        show_alert("خطا در هنگام ثبت ارزیابی. لطفا دوباره تلاش کنید.", "danger", insert_after_selector="#evaluation-submit", timeoutput=5000);
        console.error("خطا در هنگام ثبت ارزیابی:", error);
    }
}

$("#evaluation-submit").click(function () {
    // prevent default form submission
    event.preventDefault();
    submit_evaluation();
});



async function submit_feedback() {
    try {
        // get the model name by trimming out the last `-completion` part
        const model_a = $("#completion-A-col").find("xmp").attr("id").slice(0, -11);
        const model_b = $("#completion-B-col").find("xmp").attr("id").slice(0, -11);

        // get the prompt and completions
        const prompt = $("#history-message-region").find("xmp").text();
        const completion_a = $("#completion-A-col").find("xmp").text();
        const completion_b = $("#completion-B-col").find("xmp").text();

        // feedback
        const instance_quality = $("input[name='instance-quality']:checked").val();
        const comment = $("textarea[name='comment']").val();

        console.log("instance_quality:", instance_quality);
        console.log("comment:", comment);

        // make sure some fields are filled
        if ((instance_quality === undefined || instance_quality === null) && comment === "") {
            show_alert("بازخوردی ارائه نشده است.", "danger", insert_after_selector="#feedback-submit", timeout=5000);
            return;
        }
        const response = await fetch("/api/submit-feedback", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                index: current_index,
                model_a,
                model_b,
                prompt,
                completion_a,
                completion_b,
                instance_quality: instance_quality || null,
                comment,
                evaluator: username 
            }),
        });
        
        // if the response is 200, show the success message
        if (response.status == 200) {
            show_alert("بازخورد با موفقیت ثبت شد.", "success", insert_after_selector="#feedback-submit", timeoutput=5000);
            console.log("بازخورد با موفقیت ثبت شد.");
        }
        else if (response.status == 401) {
            show_alert("برای ثبت بازخورد باید وارد شوید.", "danger", insert_after_selector="#feedback-submit", timeoutput=5000);
        }
        else {
            console.log(response);
            show_alert("خطا در هنگام ثبت بازخورد. لطفا دوباره تلاش کنید.", "danger", insert_after_selector="#feedback-submit", timeoutput=5000);
            console.error("خطا در هنگام ثبت بازخورد:", response.status);
        }
    } catch (error) {
        show_alert("خطا در هنگام ثبت بازخورد. لطفا دوباره تلاش کنید.", "danger", insert_after_selector="#feedback-submit", timeoutput=5000);
        console.error("خطا در هنگام ثبت بازخورد:", error);
    }
}

$("#feedback-submit").click(function () {
    // prevent default form submission
    event.preventDefault();
    submit_feedback();
});

// Add event listeners for the navigation buttons
$('#prev-button').click(function () {
    if (current_index > 0) {
        // redirect to the previous instance using url
        window.location.href = `/instances/${current_index - 1}`;
    } else {
        show_alert("شما در حال حاضر در اولین نمونه از داده هستید.", "danger");
    }
});

$("#next-button").click(function () {
    // redirect to the next instance using url
    window.location.href = `/instances/${current_index + 1}`;
});

$("#logout-button").click(function () {
    // redirect to the logout url
    window.location.href = `/logout`;
});

$("#left-instances-button").click(function () {
    // opens left-instances url in a new tab
    window.open(`/left-instances`, '_blank');
});
