const AWS = require('aws-sdk');
const Utilities = require('../lib/Utilities')

const dynamoDb = new AWS.DynamoDB.DocumentClient();

function randomString(length, chars) {
  var result = '';
  for (var i = length; i > 0; --i) result += chars[Math.floor(Math.random() * chars.length)];
  return result;
}

function tagInstances(instances, creds, account_id) {
  var instancesByRegion = Utilities.groupBy(instances, 'region');
  var instanceTagPromises = [];
  Object.keys(instancesByRegion).map(e => {
    creds.region = e;
    var ec2WithRegion = new AWS.EC2(creds);
    instancesByRegion[e].map(instance => {
      var params = {
        Resources: [
          instance.id,
        ],
        Tags: [
          {
            Key: 'environment',
            Value: instance.env
          }
        ]
      };
      instanceTagPromises.push(ec2WithRegion.createTags(params).promise().then(result => {
        return { id: instance.id, is_tagged: true };
      }, error => {
        return { id: instance.id, is_tagged: false };
      }));
    });
  });
  return Promise.all(instanceTagPromises).then(results => {
    return results;
  });
}


function tagDatabases(databases, creds, account_id) {
  var databasesByRegion = Utilities.groupBy(databases, 'region');
  var databaseTagPromises = [];
  Object.keys(databasesByRegion).map(e => {
    creds.region = e;
    var rdsWithRegion = new AWS.RDS(creds);
    databasesByRegion[e].map(database => {
      var params = {
        ResourceName: "arn:aws:rds:" + database.region + ":" + account_id + ":db:" + database.id, /* required */
        Tags: [{
          Key: 'environment',
          Value: database.env
        }]
      };
      databaseTagPromises.push(rdsWithRegion.addTagsToResource(params).promise().then(result => {
        return { id: database.id, is_tagged: true }
      }, error => {
        console.log(error);
        return { id: database.id, is_tagged: false }
      }));
    });

  });
  return Promise.all(databaseTagPromises).then(results => {
    return results;
  });
}

function tagElasticCaches(cacheClusters, creds, account_id) {
  var cacheClustersByRegion = Utilities.groupBy(cacheClusters, 'region');
  var elasticCacheTagPromises = [];
  Object.keys(cacheClustersByRegion).map(e => {
    creds.region = e;
    var elasticCacheWithRegion = new AWS.ElastiCache(creds);
    cacheClustersByRegion[e].map(cacheCluster => {
      var ARN = "arn:aws:elasticache:" + cacheCluster.region + ":" + account_id + ":cluster:" + cacheCluster.id;
      var params = {
        ResourceName: ARN,
        Tags: [{
          Key: 'environment',
          Value: cacheCluster.env
        }]
      };
      elasticCacheTagPromises.push(elasticCacheWithRegion.addTagsToResource(params).promise().then(result => {
        return { id: cacheCluster.id, is_tagged: true }
      }, error => {
        console.log(error);
        return { id: cacheCluster.id, is_tagged: false }
      }));
    });

  });
  return Promise.all(elasticCacheTagPromises).then(results => {
    return results;
  });
}

function tagCloudFronts(cloudFronts, creds, account_id) {
  const awscloudfront = new AWS.CloudFront(creds);
  var tagCloudFrontPromises = cloudFronts.map(cloudFront => {
    var ARN = 'arn:aws:cloudfront::' + account_id + ':distribution/' + cloudFront.id;

    var params = {
      Resource: ARN,
      Tags: {
        Items: [
          {
            Key: 'environment',
            Value: cloudFront.env
          }
        ]
      }
    };
    return awscloudfront.tagResource(params).promise().then(result => {
      return { id: cloudFront.id, is_tagged: true }
    }, error => {
      console.log(error);
      return { id: cloudFront.id, is_tagged: false }
    });
  });
  return Promise.all(tagCloudFrontPromises).then(results => {
    return results;
  });
}

function tagS3Buckets(buckets, creds, account_id) {
  var s3 = new AWS.S3(creds);

  var bucketTagPromises = buckets.map(bucket => {
    var params = {
      Bucket: bucket.id,
      Tagging: {
        TagSet: [
          {
            Key: "environment",
            Value: bucket.env
          }
        ]
      }
    };
    return s3.putBucketTagging(params).promise().then(result => {
      return { id: bucket.id, is_tagged: true }
    }, error => {
      console.log(error);
      return { id: bucket.id, is_tagged: false }
    });
  });
  return Promise.all(bucketTagPromises).then(results => {
    return results;
  });

}


module.exports.tagResources = (event, context, callback) => {
  const requestData = JSON.parse(event.body);
  const email = event.requestContext.authorizer.claims['email'];
  const accountId = event.pathParameters.accountId;

  var user_params = {
    TableName: Utilities.table('users'),
    KeyConditionExpression: "#id = :email",
    ExpressionAttributeNames: {
      "#id": "id"
    },
    ExpressionAttributeValues: {
      ":email": email
    }
  };

  dynamoDb.query(user_params, (error, result) => {
    if (error) {
      console.error(error);
    }
    const user = result.Items[0]
    const params = {
      TableName: Utilities.table('cloud_service_providers'),
      Key: {
        userId: user.rootUserId,
        accountId: accountId
      },
    };

    dynamoDb.get(params, (error, result) => {
      // handle potential errors
      if (error) {
        console.error(error);
        callback(null, 'failure');
      }

      let sts = new AWS.STS({
        apiVersion: '2012-08-10'
      });
      //const account_id = result.Item.roleArn.split(':')[4]
      let stsParams = {
        RoleArn: result.Item.roleArn,
        RoleSessionName: randomString(32, '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'),
        ExternalId: result.Item.externalId
      };

      sts.assumeRole(stsParams, (err, data) => {
        if (err) {
          console.error(err);
        }
        const creds = {
          accessKeyId: data.Credentials.AccessKeyId,
          secretAccessKey: data.Credentials.SecretAccessKey,
          sessionToken: data.Credentials.SessionToken
        }
        Promise.all([
          tagInstances(requestData.instances, creds, accountId),
          tagDatabases(requestData.databases, creds, accountId),
          tagElasticCaches(requestData.cacheClusters, creds, accountId),
          tagCloudFronts(requestData.cloudFronts, creds, accountId),
          tagS3Buckets(requestData.s3Buckets, creds, accountId)
        ]).then(results => {
          var response = {};
          response.instances = results[0];
          response.databases = results[1];
          response.cacheClusters = results[2];
          response.cloudFronts = results[3];
          response.s3Buckets = results[4];

          var params = {
            TableName: Utilities.table('cloud_service_providers'),
            Key: {
              userId: user.rootUserId,
              accountId: accountId
            },
            UpdateExpression: "set isResourcesTagged = :r",
            ExpressionAttributeValues: {
              ":r": true,
            },
            ReturnValues: "UPDATED_NEW"
          };

          dynamoDb.update(params, function (err, data) {
            const apiCallResponse = {
              statusCode: 200,
              body: JSON.stringify(response),
              headers: { 'Access-Control-Allow-Origin': '*' }
            };
            callback(null, apiCallResponse);
          });

        }).catch(callback);
      })
    })
  })
}