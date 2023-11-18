// real time notification
$(document).ready(function() {
    function updateNotifications() {
        $.getJSON('/get_notifications', function(data) {
            let $notifications = $('#notification-list');
            if (data.length > 0) {
                $notifications.empty(); 
                data.forEach(function(notif) {
  
                    let $alertDiv = $('<div></div>').addClass('alert alert-info d-flex justify-content-center').attr('data-id', notif.id);
                    
                    let $messageP = $('<p></p>').addClass('notification-message').text(notif.message);
                    $alertDiv.append($messageP);
                    
                    let $actionButtonsDiv = $('<div></div>').addClass('action-buttons');
                  
                    let $acceptForm = $('<form></form>', {
                        action: "/holiday_buttons",
                        method: "post",
                        style: "display: inline;"
                    }).append(
                        $('<input>', {type: "hidden", name: "notification_id", value: notif.id}),
                        $('<input>', {type: "hidden", name: "action", value: "accept"}),
                        $('<button></button>', {type: "submit", class: "custom-button btn btn-sm bg-success"}).text("Accept")
                    );
                    $actionButtonsDiv.append($acceptForm);
                    
                    let $declineForm = $('<form></form>', {
                        action: "/holiday_buttons",
                        method: "post",
                        style: "display: inline;"
                    }).append(
                        $('<input>', {type: "hidden", name: "notification_id", value: notif.id}),
                        $('<input>', {type: "hidden", name: "action", value: "decline"}),
                        $('<button></button>', {type: "submit", class: "custom-button btn btn-sm bg-danger"}).text("Decline")
                    );
                    $actionButtonsDiv.append($declineForm);

                    $alertDiv.append($actionButtonsDiv);
                    
                    $notifications.append($alertDiv);
                });
            }
        });
    }
    setInterval(updateNotifications, 1000); 
    updateNotifications(); 
});


//  real time notification for manager
$(document).ready(function() {
    function updateManagerNotifications() {
        $.getJSON('/get_manager_notifications', function(data) {
            let $notifications = $('#notification-list');
            if (data.length > 0) {
                $notifications.empty();
                data.forEach(function(notif) {
                    let $alertDiv = $('<div></div>').addClass('alert alert-info d-flex justify-content-center').attr('data-id', notif.id);
                    $alertDiv.append($('<p></p>').addClass('notification-message').text(notif.message));
                    
                    let $actionButtonsDiv = $('<div></div>').addClass('action-buttons');

                    let $acceptForm = $('<form></form>', {
                        action: "/manager_buttons",  
                        method: "post",
                        style: "display: inline;"
                    }).append(
                        $('<input>', {type: "hidden", name: "notification_id", value: notif.id}),
                        $('<input>', {type: "hidden", name: "action", value: "accept"}),
                        $('<button></button>', {type: "submit", class: "custom-button btn btn-sm bg-success"}).text("Accept")
                    );

                    $actionButtonsDiv.append($acceptForm);

                    let $declineForm = $('<form></form>', {
                        action: "/manager_buttons",  
                        method: "post",
                        style: "display: inline;"
                    }).append(
                        $('<input>', {type: "hidden", name: "notification_id", value: notif.id}),
                        $('<input>', {type: "hidden", name: "action", value: "decline"}),
                        $('<button></button>', {type: "submit", class: "custom-button btn btn-sm bg-danger"}).text("Decline")
                    );

                    $actionButtonsDiv.append($declineForm);
                    $alertDiv.append($actionButtonsDiv);
                    $notifications.append($alertDiv);
                });
            } 
        });
    }
    setInterval(updateManagerNotifications, 1000); 
    updateManagerNotifications(); 
});
