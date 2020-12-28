'use strict';

const AWS = require('aws-sdk');
const ec2 = new AWS.EC2()
const Utilities = require('../lib/Utilities')
const dynamoDb = new AWS.DynamoDB.DocumentClient();

var paramsWithCreds = {};
var account_id = null;

var response = null;

function randomString(length, chars) {
  var result = '';
  for (var i = length; i > 0; --i) result += chars[Math.floor(Math.random() * chars.length)];
  return result;
}

function getInstancesByRegion(regionName) {
  paramsWithCreds.region = regionName;
  const ec2withRegion = new AWS.EC2(paramsWithCreds)

  return ec2withRegion.describeInstances({}).promise()
    .then(data => data.Reservations.reduce((acc, reservation) => {
      const instances = reservation.Instances.map(instance => {
        var nameTag = instance.Tags.find(tag => tag.Key === 'Name');
        return {
          id: instance.InstanceId,
          name: nameTag != null ? nameTag.Value : '',
          tags: instance.Tags,
          region: regionName
        }
      })

      return acc.concat(instances)
    }, []))
}


function getDatabasesByRegion(regionName) {
  paramsWithCreds.region = regionName;
  const rdsWithRegion = new AWS.RDS(paramsWithCreds)

  return rdsWithRegion.describeDBInstances({}).promise()
    .then(data => {
      const dbinstance_with_tags = data.DBInstances.map(dbInstance => {
        return rdsWithRegion.listTagsForResource({ ResourceName: "arn:aws:rds:" + regionName + ":" + account_id + ":db:" + dbInstance.DBInstanceIdentifier }).promise()
          .then(tagResourceTag => {
            return {
              id: dbInstance.DBInstanceIdentifier,
              name: dbInstance.DBInstanceIdentifier,
              tags: tagResourceTag.TagList,
              region: regionName
            };
          });
      });
      return Promise.all(dbinstance_with_tags);
    });
}

function getElasticCachesByRegion(regionName) {
  paramsWithCreds.region = regionName;
  var elasticacheWithRegion = new AWS.ElastiCache(paramsWithCreds);
  return elasticacheWithRegion.describeCacheClusters({}).promise()
    .then(data => {
      const elasticcache_with_tags = data.CacheClusters.map(cacheCluster => {
        return elasticacheWithRegion.listTagsForResource({ ResourceName: "arn:aws:elasticache:" + regionName + ":" + account_id + ":cluster:" + cacheCluster.CacheClusterId }).promise()
          .then(tagResourceTag => {
            return {
              id: cacheCluster.CacheClusterId,
              name: cacheCluster.CacheClusterId,
              tags: tagResourceTag.TagList,
              region: regionName
            };
          });
      });
      return Promise.all(elasticcache_with_tags);
    })
}

function getResourcesByRegion(region) {
  return Promise.all([
    getInstancesByRegion(region),
    getDatabasesByRegion(region),
    getElasticCachesByRegion(region),
  ])
    .then(results => {
      response.instances = response.instances.concat(results[0]);
      response.databases = response.databases.concat(results[1]);
      response.cacheClusters = response.cacheClusters.concat(results[2]);
      return response;
    })
}

function getCloudFronts() {
  const awscloudfront = new AWS.CloudFront(paramsWithCreds);

  return awscloudfront.listDistributions({}).promise()
    .then(data => {
      const cloudfront_with_tags = data.DistributionList.Items.map(cloudfront => {
        return awscloudfront.listTagsForResource({ Resource: cloudfront.ARN }).promise()
          .then(tagResourceTag => {
            return {
              id: cloudfront.Id,
              name: cloudfront.DomainName,
              region: 'global',
              tags: tagResourceTag.Tags.Items
            };
          });
      });
      return Promise.all(cloudfront_with_tags);
    })
}

function getS3Buckets() {
  var s3 = new AWS.S3(paramsWithCreds);

  return s3.listBuckets().promise()
    .then(data => {
      const s3_with_tags = data.Buckets.map(bucket => {
        return s3.getBucketTagging({ Bucket: bucket.Name }).promise()
          .then(resourceTags => {
            return { id: bucket.Name, name: bucket.Name, region: 'global', tags: resourceTags.TagSet }
          }).catch(error => {
            console.log("Error occurred");
            console.log(error);
            return { id: bucket.Name, name: bucket.Name, region: 'global', tags: [] }
          });
      });
      return Promise.all(s3_with_tags);
    });
}

module.exports.listResources = (event, context, callback) => {
  const data = JSON.parse(event.body);
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
      if (error) {
        console.error(error);
      }

      let sts = new AWS.STS({
        apiVersion: '2012-08-10'
      });
      account_id = result.Item.roleArn.split(':')[4]
      let stsParams = {
        RoleArn: result.Item.roleArn,
        ExternalId: result.Item.externalId,
        RoleSessionName: randomString(32, '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
      };

      sts.assumeRole(stsParams, (err, data) => {
        if (err) {
          console.error(err);
        }
        response = { instances: [], databases: [], cacheClusters: [], cloudFronts: [], s3Buckets: [] };
        paramsWithCreds = {
          accessKeyId: data.Credentials.AccessKeyId,
          secretAccessKey: data.Credentials.SecretAccessKey,
          sessionToken: data.Credentials.SessionToken
        }
        ec2.describeRegions({})
          .promise()
          .then((data) => {
            const getResources = data.Regions
              .map(region => getResourcesByRegion(region.RegionName))

            return Promise.all(getResources)
          })
          .then(resources => {
            return Promise.all([
              getCloudFronts(),
              getS3Buckets()
            ]).then(results => {
              response.cloudFronts = results[0];
              response.s3Buckets = results[1];

              const apiCallResponse = {
                statusCode: 200,
                body: JSON.stringify(response),
                headers: { 'Access-Control-Allow-Origin': '*' }
              };
              callback(null, apiCallResponse);
            }).catch(callback)
          })
          .catch(callback)
      });

    });
  });
}
