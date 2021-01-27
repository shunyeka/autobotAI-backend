# Installation steps.

* Install Python3 3.6
* Install VirtualEnv

```bash
pip3 install virtualenv
```

* Create venv in autobot-async

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
NodeJS version 8.0.x for serverless.

# Serverless

## Install Serverless Framework via npm (works for both Windows and Linux)
* Note: Make sure that you already have installed Node v6 or higher on your server.
* To install the Serverless Framework via npm which was already installed when you installed Node.js, Open up a terminal and type **npm install -g serverless** to install Serverless.
```
npm install -g serverless
```
* Once the installation process is done you can verify that Serverless is installed successfully by running the following command in your terminal:
```
serverless
```

## AWS - Deploy

* The **sls deploy** command deploys your entire service via CloudFormation. Run this command when you have made infrastructure changes (i.e., you edited **serverless.yml**). Use **serverless deploy function -f myFunction** when you have made code changes and you want to quickly upload your updated code to AWS Lambda or just change function configuration.

```
serverless deploy
```
## Options for Serverless Deploy

*  --config or -c Name of your configuration file, if other than serverless.yml|.yaml|.js|.json.
*  --stage or -s The stage in your service that you want to deploy to.
*  --region or -r The region in that stage that you want to deploy to.
*  --package or -p path to a pre-packaged directory and skip packaging step.
*  --verbose or -v Shows all stack events during deployment, and display any Stack Output.
*  --force Forces a deployment to take place.
*  --function or -f Invoke deploy function (see above). Convenience shortcut - cannot be used with --package.
*  --conceal Hides secrets from the output (e.g. API Gateway key values).
*  --aws-s3-accelerate Enables S3 Transfer Acceleration making uploading artifacts much faster. You can read more about it here. It requires additional s3:PutAccelerateConfiguration permissions. Note: When using Transfer Acceleration, additional data transfer charges may apply.
*  --no-aws-s3-accelerate Explicitly disables S3 Transfer Acceleration. It also requires additional s3:PutAccelerateConfiguration permissions.

## Deployment with stage and region options

```
serverless deploy --stage production --region ap-south-1
```
## Add Resource Based Policy To Lambda Function.

* After successfully deployment of  the serverless template we can update permission for  resource based policy of post confirmation lambda function by running the below command from aws cli.
* Note: Resource based policy of lambda function can only be update from AWS CLI.

```bash
aws lambda add-permission --function-name autobot-api-test-congintoUserCreateConfirm --action lambda:InvokeFunction --statement-id postConfirmation --principal cognito-idp.amazonaws.com
aws lambda remove-permission --function-name autobot-api-test-congintoUserCreateConfirm --statement-id postConfirmation
```