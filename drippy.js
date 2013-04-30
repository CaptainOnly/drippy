function green_update() {
    $.post("green", function(data) {
        $("#green_state").text("Green is " + data);
    });

    $.post("green_schedule", function(data) {
        $("#green_schedule").html(data);
    });
    
    $.post("green_table", function(data) {
        $("#green_table").html(data);
    });
};

// <div id="state"></div>
// <div id="schedule"></div>
// <form id="form">
// <input id="off"        type='submit' value='Off'>
// <input id="on"         type='submit' value='On'>
// <input id="time_2"     type='radio'  name='time' value='2'>2 hours
// <input id="time_4"     type='radio'  name='time' value='4'>4 hours
// <input id="time_x"     type='radio'  name='time' value='x'>This many hours:
// <input id="time_x_val" type='text'   disabled='disabled='>
// </form>
// <div id="table"></div>

function zone_div(zone_name) {
    $("#zone_list").append('<div class="zone_div" id="' + zone_name + '"></div>');
    $("#" + zone_name).append('<br>');
    $("#" + zone_name).append(zone_name);
    $("#" + zone_name).append('<div id="state"></div>');
    $("#" + zone_name).append('<div id="schedule"></div>');
    $("#" + zone_name).append('<form id="form">');
    $("#" + zone_name).append('<input id="off"        type="submit" value="Off">');
    $("#" + zone_name).append('<input id="on"         type="submit" value="On">');
    $("#" + zone_name).append('<input id="time_2"     type="radio"  name="time" value="2">2 hours');
    $("#" + zone_name).append('<input id="time_4"     type="radio"  name="time" value="4">4 hours');
    $("#" + zone_name).append('<input id="time_x"     type="radio"  name="time" value="x">This many hours:');
    $("#" + zone_name).append('<input id="time_x_val" type="text"   disabled="disabled">');
    $("#" + zone_name).append('</form>');
    $("#" + zone_name).append('<div id="table"></div>');

    // Enable/Disable the numeric field depending on radio selection

    $("#" + zone_name + " > #time_2").change(function () {
        $("#" + zone_name + " > #time_x_val").prop("disabled", true);
    });
    $("#" + zone_name + " > #time_4").change(function () {
        $("#" + zone_name + " > #time_x_val").prop("disabled", true);
    });
    $("#" + zone_name + " > #time_x").change(function () {
        $("#" + zone_name + " > #time_x_val").prop("disabled", false);
    });

    // Send the "on" message

    $("#" + zone_name + " > #on").click(function () {
        $.post("zone_control", { 
            OnOff: "ON",
            OnSelect: $("#" + zone_name + " > input[name=time]:checked", '#green_form').val(),
            OnParam: $("#green_time_x_val").val() }, function(data) {
		green_update();
            });

        return false;
    });

};

$(document).ready(function() {
    
    // Get the zones and create zone divs for them
    $.get("zone_list", function(data) {
        var zone_array = jQuery.parseJSON(data);
	zone_array.forEach( zone_div );
    });


    $("#green_off").click(function () {
        $.post("green_control", { OnOff: "OFF" }, function(data) {
            green_update();
        });
        return false;
    });
});
