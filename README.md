new-tab-dashboard
=================

Custom new tab page for web browsers. Uses python2 / flask to render a page with javascript graphs of system load and other things.

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

If you do decide to run my new tab page, let me know! I'm very open to pull requests and suggestions from others.
