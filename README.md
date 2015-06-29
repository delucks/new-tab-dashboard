new-tab-dashboard
=================

Easily extensible "new tab" page framework for Linux/UNIX. Based around the concept of column widgets that display anything you can output from python. These widgets are dynamically loaded to keep a low memory footprint while still remaining useful.

Technical Details
-----------------

Uses python2 / flask to render a page with javascript graphs from the Google Charts API. Currently implemented in a client/server model, with the server running in the background and rendering a page which the web browser "client" consumes.

Screenshots
-----------

Top of the page:

![](http://cluster.lug.udel.edu/~jluck/new-tab-overview.png)

Memory summary graph:

![](http://cluster.lug.udel.edu/~jluck/new-tab-mem.png)

Spotify integration:

![](http://cluster.lug.udel.edu/~jluck/new-tab-spotify.png)

Installation
------------

You're a brave soul!

1. Install all the python modules mentioned in `requirements.txt`.
2. Download this repository, and remember where you put it.
3. Run `python2 newtab-server.py`, and let this fork to the background (I'm still working on accurately daemonizing it).

For showing this as your new tab page, you have a few options:

### Chrome Extension

Open up the "Extensions" menu option of Chrom{e,ium}, "Load unpacked extension", and navigate to the directory you downloaded this project to.
This will override the new-tab page to be an iframe displaying `http://localhost:9001` by default.
If newtab-server.py is running, you'll see your (new) new tab page!

### Native Firefox/Chrome

Change your homepage to `http://localhost:9001`, and set your new tab policy to "open my homepage".

Writing your own widgets
------------------------

Creating your own column widgets is straightforward. First, define a class which inherits from Column inside `newtab-server.py`. You must define a `get_data()` method which returns a dictionary of data to be merged into the Flask request context. Additionally, you must write a template file which the class should display. This is noted in the class with the `template_path` attribute, a string containing the name of the template file inside of the `templates/` dir. All the display logic is up to you, just make sure that all your dynamic content has the same name in the template as the dictionary returned by `get_data()`.

If you do decide to run my new tab page, let me know! I'm very open to pull requests and suggestions from others.
