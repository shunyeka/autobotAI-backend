# Installation steps.

* Install Python3 3.6
* Install VirtualEnv

```bash
pip3 install virtualenv
```

* Create venv in autobot-asyn

```bash
cd pathto_autobot-async/
python3 -m venv venv
source venv/bin/activate
```

* Install required packages

```bash
pip install flask-ask
pip install -U pylint
pip install -U autopep8
pip install -U boto3
pip install --upgrade flask-ask
pip install --upgrade flask-cors
pip install python-dateutil
```

* Try the following if you face any error.


```bash
pip install -U 'cryptography<2.2'
```
nvm use 6.10.3
npm install --save-dev serverless-domain-manager
npm install --save-dev serverless-wsgi serverless-python-requirements
serverless-wsgi




# Windows

Note: Only works with Python 3.6

## Install miniconda
https://docs.conda.io/en/latest/miniconda.html

##


# TODO

- Add new env setup preparation
- Add serverless.yml related documentation
- Add config.py related documentation


export LDFLAGS="-L/usr/local/opt/openssl@1.1/lib"
export CPPFLAGS="-I/usr/local/opt/openssl@1.1/include"
pip install cryptography --global-option=build_ext --global-option="-L/usr/local/opt/openssl/lib" --global-option="-I/usr/local/opt/openssl/include"
