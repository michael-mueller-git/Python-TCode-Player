# Python TCode Controler

App to play funscripts on your tcode serial devices. Supported video players are [MPV](https://mpv.io/) and [Whirligig](http://www.whirligig.xyz/).

## Build Application from Source

### Windows 10

We use [pyinstaller](https://pypi.org/project/pyinstaller/) in [miniconda](https://docs.conda.io/en/latest/miniconda.html) environment to create an Windows executable.

First download and install [miniconda](https://docs.conda.io/en/latest/miniconda.html) (If you have already [anaconda](https://www.anaconda.com/) installed on your computer you can skip this step). Then run the following commands in the project root directory:

```
conda env create -f environment_windows.yaml
conda activate tcode-player
build.bat
```

This create the Windows executable in `./dist`.

Finally you can remove the build environment with `conda env remove -n tcode-player`.
