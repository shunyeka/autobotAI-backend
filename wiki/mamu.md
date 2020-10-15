# Steps to Release Multi Accounts Multi Users

* Generate autobotAIDeploy.template by running the app locally and calling the following URL.

```http://localhost:5000/api/v1/public/aws/cloudFormationTemplate```

* Change the `Environment` default value based on the env i.e. `Staging` or `Live`
* Compare the file with previous file stored in `templates` directory
* The following is the files
    * Bucket: `autobot-ai`
    * Lambda Zip file: `AutobotSetup-<Env>.zip`
    * CloudFormation template: `autobotIAMDeploy-<Env>.template`    
* Create lambda zip file and upload to s3 and make them public

- Make sure to deploy the following applications
    - autobot-async
    - autobot-web
    - autobot-api
- Make sure to upload account setup zip and cf template by generating through main application.
    - AutobotAISetup-Live.zip
    - AutobotAISetup-Staging.zip
    - autobotAIDeployment.yml
- Migrate cloud_service_provider to cloud_service_providers
- Migrate user to users.
- Update the user create trigger lambda function