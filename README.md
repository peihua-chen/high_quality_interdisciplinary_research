# Interdisciplinary Impact: Scripts and Data
Last update: July 29, 2020

This repository contains all the data and code necessary to reproduce the data and results that drive the paper. The data collecting script (main.py) runs with files in the Data folder. Analysis is conducted and figures generated in Data_Analysis_v1.ipynb.


## Getting Started

These instructions will get you a copy of the project up and running on your local machine.


### Prerequisites

* Python 3 (developed on 3.7.6; unknown if project will work with Python 2.7)
* Python libraries: requests, pandas, unidecode
* RStudio/Jupyter Notebook with R kernel


### Setup

1. Clone the repository.
2. Run main.py line by line in an interactive shell, saving the files along the way, since due to Scopus API limit (20,000 calls/week) it will not be possible to pull all the records at once.
3. Run Data_Analysis_v1.ipynb in Jupyter Notebook. You can run Data_Analysis_v1.ipynb in Jupyter Notebook with the files called from Google Drive, or you can re-pull all the files.


## Authors

* **Pei Hua Chen**
* **Eli Fenichel**


## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details


## Acknowledgments

* Inspiration from [PyScopus](http://zhiyzuo.github.io/python-scopus/) and [ElsaPy](https://github.com/ElsevierDev/elsapy)