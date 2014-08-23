# Great Run Websites processing files

These files do interesting things in terms of HTML scraping Great Run results websites *and* then processing them to rebuild the dataset and then do some analysis on it.

The main features are:

* Python scripts to fetch the pages.
* Python scripts to process the results and generate CSV files.
* iPython Notebooks that analyse the results.

## Getting Matplotlib installed on OS X Mavericks.

From [here](https://github.com/rueckstiess/mtools/wiki/matplotlib-Installation-Guide):

```bash
sudo mkdir -p /usr/local/include
sudo ln -s /usr/X11/include/freetype2/freetype /usr/local/include/freetype
sudo ln -s /usr/X11/include/ft2build.h /usr/local/include/ft2build.h
# The following 3 already existed (probably due to Homebrew)
sudo ln -s /usr/X11/include/png.h /usr/local/include/png.h
sudo ln -s /usr/X11/include/pngconf.h /usr/local/include/pngconf.h
sudo ln -s /usr/X11/include/pnglibconf.h /usr/local/include/pnglibconf.h

sudo mkdir -p /usr/local/lib
sudo ln -s /usr/X11/lib/libfreetype.dylib /usr/local/lib/libfreetype.dylib
sudo ln -s /usr/X11/lib/libpng.dylib /usr/local/lib/libpng.dylib
```

and then:

```bash
pip install matplotlib
```

