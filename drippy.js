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

function zone_div(zone_id, zone_name) {
    $("#zone_list").append('<div class="zone_div" id="' + zone_id + '"></div>');
    $("#" + zone_id).append('<div id="name"></div>');
    $("#" + zone_id).append('<div id="state"></div>');
    $("#" + zone_id).append('<div id="schedule"></div>');
    $("#" + zone_id).append('<form id="form">');
    $("#" + zone_id).append('<input id="off"        type="submit" value="Off">');
    $("#" + zone_id).append('<input id="on"         type="submit" value="On">');
    $("#" + zone_id).append('<input id="time_2"     type="radio"  name="' + zone_id + '_time" value="2">2 hours');
    $("#" + zone_id).append('<input id="time_4"     type="radio"  name="' + zone_id + '_time" value="4">4 hours');
    $("#" + zone_id).append('<input id="time_x"     type="radio"  name="' + zone_id + '_time" value="x">This many hours:');
    $("#" + zone_id).append('<input id="time_x_val" type="text"   disabled="disabled">');
    $("#" + zone_id).append('</form>');
    $("#" + zone_id).append('<div id="table"></div>');

    // Enable/Disable the numeric field depending on radio selection

    $("#" + zone_id + " > #time_2").change(function () {
        $("#" + zone_id + " > #time_x_val").prop("disabled", true);
    });
    $("#" + zone_id + " > #time_4").change(function () {
        $("#" + zone_id + " > #time_x_val").prop("disabled", true);
    });
    $("#" + zone_id + " > #time_x").change(function () {
        $("#" + zone_id + " > #time_x_val").prop("disabled", false);
    });

    // Check the two hour radio button by default

    $("#" + zone_id + " > input[value=2]").prop('checked', true);

    // Define a method for updating the zone

    var update_function = function(data) {
	$.post("zone_state", { ID: zone_id }, function(data) {
            $("#" + zone_id + " > #name").text(zone_name + " is " + data);
	});

	// $.post("green_schedule", function(data) {
        //     $("#" + zone_id + " > #schedule").html(data);
	// });
    
	// $.post("green_table", function(data) {
        //     $("#" + zone_id + " > #table").html(data);
	// });
    };

    // Update once a second

    setInterval(update_function, 1000);

    // Send the "on" message when "on" clicked

    $("#" + zone_id + " > #on").click(function () {
        $.post("zone_control", { 
	    ID: zone_id,
            OnOff: "ON",
            OnSelect: $("#" + zone_id + " > input[name=" + zone_id + "_time]:checked").val(),
            OnParam: $("#" + zone_id + " > #time_x_val").val() }, update_function);

        return false;
    });

    // Send the "off" message when "off" clicked

    $("#" + zone_id + " > #off").click(function () {
        $.post("zone_control", {
	    ID: zone_id,
            OnOff: "OFF" }, update_function ); 

        return false;
    });
};

$(document).ready(function() {
    
    // Get the zones and create zone divs for them

    $.get("zone_list", function(data) {
        var zone_array = jQuery.parseJSON(data);
	zone_array.forEach( function(zone) {
	    zone_div(zone['ID'], zone['Name']);
	    $("#zone_list").append('<br>');
	});
    });
});
