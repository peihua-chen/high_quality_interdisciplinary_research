# Interdisciplinary Impact: Scripts and Data
Last update: June 12, 2020

This repository contains all the data and code necessary to reproduce the data and results that drive the paper. The data collecting script (pullScopus.py) runs with files in the Data folder. Analysis is conducted and figures generated in Data_Analysis.ipynb.


## Getting Started

These instructions will get you a copy of the project up and running on your local machine.


### Prerequisites

* Python 3 (developed on 3.7.6; unknown if project will work with Python 2.7)
* Python libraries: requests, pandas, unidecode
* RStudio/Jupyter Notebook with R kernel


### Setup

Clone the repository. I recommend running pullScopus.py in an interactive shell. Data_Analysis.ipynb runs in Jupyter Notebook.

You may want to run the lines in the main function of pullScopus.py one by one in an interactive shell, saving the files along the way, since due to Scopus API limit (20,000 calls/week) it will not be possible to pull all the records at once.

You can run Data_Analysis.ipynb in Jupyter Notebook with the files called from Google Drive, or you can re-pull all the files.

Note that this project was developed on Windows 10, so the "\\" characters in file paths may need to be changed to "/" for other Linux/Mac.

## Authors

* **Pei Hua Chen**
* **Eli Fenichel**


## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details


## Acknowledgments

* Inspiration from PyScopus (http://zhiyzuo.github.io/python-scopus/) and ElsaPy (https://github.com/ElsevierDev/elsapy)