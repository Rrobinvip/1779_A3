
function loading(){
    var clicked = document.getElementById('label_1').onclick
    if (clicked){
        console.log('Clicked!')
        $(".loader-wrapper").fadeIn("slow");
    }
    // $("#content").hide(); 
}

$(window).on("load",function(){
    $(".loader-wrapper").fadeOut("slow");
});