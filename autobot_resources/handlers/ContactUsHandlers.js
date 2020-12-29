'use strict';
const AWS = require('aws-sdk');
const ContactInfo = require('../lib/ContactInfo')
const Utilities = require('../lib/Utilities')
const https = require('https');
const querystring = require('querystring');
const gRecaptchaSecret = 'xxxxxxxxxxxxxxxxxxxxxxxxxxx';

function sendEmail(bodyJson) {
  var params = {
    Destination: {
      ToAddresses: [
        'amit@autobot.live',
        'tejas@autobot.live'
      ]
    },
    Message: {
      Body: {
        Text: {
          Charset: "UTF-8",
          Data: JSON.stringify(bodyJson)
        }
      },
      Subject: {
        Charset: 'UTF-8',
        Data: 'New ContactUs Request received'
      }
    },
    Source: 'amit@autobot.live',
  };
  return new AWS.SES({ apiVersion: '2010-12-01' }).sendEmail(params).promise();
}

function validateCaptcha(response) {
  var body = '';
  var requestData = querystring.stringify({
    'response': response,
    'secret': gRecaptchaSecret
  });

  var optionspost = {
    host: 'www.google.com',
    path: '/recaptcha/api/siteverify',
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  };

  return new Promise((resolve, reject) => {
    var postReqest = https.request(optionspost, function (res) {
      res.on('data', function (chunk) {
        body += chunk;
      });
      res.on('error', function (err) {
        console.error(err);
        reject({ 'success': true, 'error_code': 'CI_INVALID_CATCHA', 'error_message': 'Captcha Validation failed' });
      });
      res.on('end', function () {
        console.log(bodyJson);
        var bodyJson = JSON.parse(body);
        if (bodyJson.success == true) {
          resolve(true);
        } else {
          resolve(false);
        }
      });
    });
    postReqest.write(requestData);
    postReqest.end();
  });
}

module.exports.send = (event, context, callback) => {
  console.log(event['requestContext']['identity']);
  var userId = JSON.stringify(event['requestContext']['identity']);
  const requestData = JSON.parse(event.body);
  validateCaptcha(requestData['g-recaptcha-response']).then((cvResponse) => {
    console.log("CV Response"+cvResponse);
    if (!cvResponse) {
      callback(null, Utilities.buildResponse(422, { 'success': true, 'error_code': 'CI_INVALID_CATCHA', 'error_message': 'Captcha Validation failed' }));
      return;
    }
    sendEmail(requestData).then((data) => {
      console.log('send mail succeeded');
      console.log(data.MessageId);
    }).catch((error)=> { console.log(error) }).then(() => {
      var contactInfo = new ContactInfo(requestData.contactEmail, requestData.contactPhone, requestData.contactName, requestData.contactMessage, userId);
      contactInfo.save().then((data) => {
        console.log('contact info save succeeded');
        callback(null, Utilities.buildResponse(200, { success: true }));
      }, (error) =>{
        console.error('contact info save failed');
        callback(null, Utilities.buildResponse(422, error));
      }).catch((error) => {
        console.error('Erro while building response after contact info save');
        callback(null, Utilities.buildResponse(422, error));
      });
    });
  }, (error) => {
    console.error("Captcha validation failed");
    console.error(error, error.stack);
    callback(null, Utilities.buildResponse(422, error));
  }).catch((error) => {    
    console.error("Error occrued while saving and sending");
    console.error(error, error.stack);
    callback(null, Utilities.buildResponse(422, error));
  });
}