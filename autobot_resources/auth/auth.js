'use strict';
const AWS = require('aws-sdk'); // eslint-disable-line import/no-extraneous-dependencies
const uuidv4 = require('uuid/v4');
const Utilities = require('../lib/Utilities')
const dynamoDb = new AWS.DynamoDB.DocumentClient();
const querystring = require('querystring');

module.exports.authInit = (event, context, callback) => {
  const requestData = event.queryStringParameters;

  var authToken = uuidv4();
  if (requestData == null || requestData.redirect_uri == null || requestData.client_id == null || requestData.response_type == null || requestData.state == null){
    callback(null, {
      statusCode: 422,
      body: {error_message: "Unable to Initiate Auth"},
      headers: {'Access-Control-Allow-Origin': '*'}
    })
    return;
  }
  let timestamp = new Date().getTime();
  const params = {
    TableName: Utilities.table('oauth'),
    Item: {
      redirectUri: requestData.redirect_uri,
      clientId: requestData.client_id,
      responseType: requestData.response_type,
      state: requestData.state,
      authToken: authToken,
      createdAt: timestamp,
      updatedAt: timestamp,
    },
  };
  // write the todo to the database
  dynamoDb.put(params, (error) => {
    // handle potential errors
    if (error) {
      console.error(error);
      callback(null, {
        statusCode: error.statusCode || 501,
        headers: { 'Content-Type': 'text/plain', 'Access-Control-Allow-Origin': '*' },
        body: 'Couldn\'t create the user.',
      });
      return;
    }
    var redirectURL = process.env.STAGE == 'staging'? "https://staging.autobot.live/auth.html?authToken=" : "https://autobot.live/auth.html?authToken=";
    const response = {
      statusCode: 302,
      headers: {
        "Location": redirectURL+authToken
      },
      body: ""
    };
    callback(null, response);
    return;
  });

}

module.exports.callback = (event, context, callback) => {
  const requestData = event.queryStringParameters;
  const authEmail = event.requestContext.authorizer.claims['email'];
  console.log("Authorized Email"+authEmail);

  const params = {
    TableName: Utilities.table('oauth'),
    Key: {
      authToken: requestData.authToken,
    },
  };
  
  dynamoDb.get(params, (error, oauthResult) => {
    if (error) {
      console.error(error);
      callback(null, {
        statusCode: error.statusCode || 422,
        headers: { 'Content-Type': 'text/plain', 'Access-Control-Allow-Origin': '*' },
        body: 'Couldn\'t find the oauthToken.',
      });
      return;
    }
    console.log("No error in getting oauthResult");   
    var user_params = {
      TableName: Utilities.table('users'),
      KeyConditionExpression: "#id = :email",
      ExpressionAttributeNames: {
        "#id": "id"
      },
      ExpressionAttributeValues: {
        ":email": authEmail
      }
    };
    dynamoDb.query(user_params, (error, users) => {
      if (error) {
        console.error(error);
      }
      console.log("No error in getting users");       
      const user = users.Items[0]
      var params = {
        TableName: Utilities.table('users'),
        Key: {
          id: authEmail,
          rootUserId: user.rootUserId,
        },
        UpdateExpression: "set accessToken = :r",
        ExpressionAttributeValues: {
          ":r": requestData.authToken,
        },
        ReturnValues: "UPDATED_NEW"
      };
  
      dynamoDb.update(params, function (err, data) {
        if(err){
          console.error(err);
          callback(null, {
            statusCode: 501,
            body: {error_message: "Tokne Generation failed"},
            headers: {'Access-Control-Allow-Origin': '*'}
          })
          return;
        }
        console.log("No error in updating toke");
        console.log(oauthResult.Item)
        let redirectURL = oauthResult.Item.redirectUri+"#";
        redirectURL += querystring.stringify({state: oauthResult.Item.state, access_token: oauthResult.Item.authToken, token_type: 'Bearer'});
        console.log("Final URL is = "+redirectURL)
        callback(null, {
          statusCode: 200,
          body: JSON.stringify({ redirectURL: redirectURL }),
          headers: {'Access-Control-Allow-Origin': '*'}
        })
        return;
      });
    });
  });
};
