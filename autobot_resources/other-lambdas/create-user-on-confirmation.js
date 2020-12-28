var aws = require('aws-sdk');
const Utilities = require('../lib/Utilities')

//var ses = new aws.SES();

const dynamoDb = new aws.DynamoDB.DocumentClient();

function sendWelcomeEmail(email, name) {
  var params = {
    Destination: { /* required */
      ToAddresses: [
        email,
      ]
    },
    Source: 'autobotAI <contact@autobot.live>',
    /* required */
    Template: 'WelcomeTemplate',
    /* required */
    TemplateData: '{ \"name\": "' + name + '" }',
    ReplyToAddresses: [
      'autobotAI <contact@autobot.live>',
    ],
  };


  // Create the promise and SES service object
  var sendPromise = new aws.SES({
    apiVersion: '2010-12-01'
  }).sendTemplatedEmail(params).promise();

  // Handle promise's fulfilled/rejected states
  return sendPromise.then(
    function (data) {
      console.log(data);
    }).catch(
      function (err) {
        console.error(err, err.stack);
      });
}

exports.handler = function (event, context) {
  console.log(event)
  var attributes = event.request.userAttributes;
  const timestamp = Utilities.timestamp();  
  if (attributes.email) {
    if (attributes.hasOwnProperty('custom:type') && attributes['custom:type'] == 'SUBUSER') {      
      var params = {
        TableName: Utilities.table('users'),
        Key: {
          id: attributes.email,
          rootUserId: attributes['custom:root_user'],
        },
        UpdateExpression: "set isActive = :ia, updatedAt = :ua",
        ExpressionAttributeValues: {
          ":ia": true,
          ":ua": timestamp
        },
        ReturnValues: "UPDATED_NEW"
      };
      dynamoDb.update(params, function (err, data) {        
        if(err){
          console.error(err);
          context.done(null, event);
        }
        try {
          sendWelcomeEmail(attributes.email, attributes.given_name).then(function () {
            context.done(null, event);
          });
        } catch (error) {
          console.log(error);
        }
      });
    } else {      
      const params = {
        TableName: Utilities.table('users'),
        Item: {
          id: attributes.email,
          rootUserId: attributes.email,
          name: attributes.given_name,
          phone: attributes.phone_number,
          userType: 'ROOT',
          isActive: true,
          createdAt: timestamp,
          updatedAt: timestamp,
        },
      };

      // write the todo to the database
      dynamoDb.put(params, (error) => {
        // handle potential errors
        if (error) {
          console.error(error);
          context.done(null, event);
        }
        try {
          sendWelcomeEmail(attributes.email, attributes.given_name).then(function () {
            context.done(null, event);
          });
        } catch (error) {
          console.log(error);
        }
      });
    }


  } else {
    context.done(null, event);
  }
};