First time on Github. Don't hate me. =P


I know this script is horribly unoptimized and can be cleaned up in so many different ways. BUT IT WORKS! (as of 4/1/24) 



Aruba-Switch-GUI.py is a GUI that uses Kivy, Paramiko and Orionsdk to create an interactive switch GUI.

This script is confirmed to work with Aruba 6200F switches. 


Sadly this program does not support resizing or probably any screen resolution other than 1920x1080 just because of the way I placed the buttons on the screen using manual coordinates because I dont know how to make the coordinates dynamic.

(This does use one png image file that should be included in the directory that the .py file is saved in. That PNG can be found here. https://imgur.com/a/7vn7xOu )



Once a switch is selected an SSH connection will be made to determine how many switches are in the stack
This script has been confirmed to work with stack sizes of 1-8 switches

A GUI will open with 52 buttons representing switch ports, a Home button which will clear all variables and move back to the home screen to select another switch, and Next/Previous Switch buttons.
These buttons will change the active switch. This is limited by however many switches are in the stack.
If the active switch is 1, then information about switch 1 will be provided, if the active switch is 2, then information about switch 2 will be provided, so on and so forth.

There is a show counters button that will turn buttons/ports with 0 counters green while leaving everything else the default color

The switch port buttons can be clicked to get the port configuration.

And thats about it.
