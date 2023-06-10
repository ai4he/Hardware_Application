# Instructions

This application detects windows in a monitor from a screen stream. It gives track of the different 
windows, extract the text from the title bar, and inserts the activity of windows in a SQLite database. 
The windows are detected by matching the image templates template_active.png and template_inactive.png 
that validate that a detected square that contains any of these templates is a valid window. You might 
need to take a screenshot of the window action buttons (the maximize, minimize, and close buttons of the 
title bar) of your operating system to make it work.

Run the following commands:

> pip install -r requirements.txt

> python3 app.py --monitor 0


