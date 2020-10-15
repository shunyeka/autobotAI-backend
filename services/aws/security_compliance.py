from services.aws.aws import AWS


class SecurityCompliance:

    @staticmethod
    def get_latest_security_compliance_data():
        response = AWS.get_dashboard_data()
        card_body = ""
        speech_output = "In my security analysis i have found that "
        recon = False

        if response['securityIssues']['adminRoles']['count'] > 1 or response['securityIssues']['adminUsers']['count'] > 3:
            speech_output += "You are not applying least privilege policy in your AWS account. there are "
            is_user = False
            if response['securityIssues']['adminUsers']['count'] > 3:
                speech_output += str(response['securityIssues']['adminUsers']['count']) + " IAM users "
                is_user = True
                card_body += "\nUsers with administrator Access: " + ",".join(response['securityIssues']['adminUsers']['itemList']) + "\n"
            if response['securityIssues']['adminRoles']['count'] > 1:
                if is_user:
                    speech_output += "and "
                speech_output += str(response['securityIssues']['adminRoles']['count']) + """
                    IAM Roles configured with full administrator privilege. 
                    AWS EC2 roles with administrator access can lead to malicious attack on AWS infrastructure.
                    """
                card_body += "\nIAM Role with administrator Access: " + ",".join(response['securityIssues']['adminRoles']['itemList']) + "\n"
            else:
                if is_user:
                    speech_output += " are configured with full administrator level access. "

            speech_output += " As per the Forrester study in 2016, misuse of privilege is causing 80% of security breaches. Its highly recommended to create least privilege access policy for Operating system and AWS level users. "

        if response['securityIssues']['unusedAccessKeys']['count']:
            speech_output += str(
                response['securityIssues']['unusedAccessKeys']['count']) + " Access keys has not been used more then 100 days. As per the security best practice, you should remove old unused access keys. "
            recon = True

        if response['securityIssues']['expiredAccessKeys']['count']:
            speech_output += str(response['securityIssues']['expiredAccessKeys']['count']) + " Access keys wasn't rotated in past 6 months, "
            recon = True

        if response['securityIssues']['passwordPolicy']['score'] < 6:
            speech_output += "Your IAM password policy is not enforcing user to set complex password, You should configure password policy that enforce upper case, lower case, numbers, special charecters, and password length more then 8 charecters. "
            recon = True

        if response['securityIssues']['usersWithoutMFA']['count']:
            speech_output += str(response['securityIssues']['usersWithoutMFA']['count']) + " AWS IAM users has not enabled multi factor authentication, "
            card_body += "IAM users without MFA: " + ", ".join(response['securityIssues']['usersWithoutMFA']['itemList']) + "\n"
            recon = True

        if response['securityIssues']['unusedIAMUsers']['count']:
            speech_output += str(response['securityIssues']['unusedIAMUsers']['count']) + " AWS IAM users has not logged in more then 30 days, such type of users can increase the risk of unauthorized access. "
            card_body += "\n AWS IAM user accounts in high risk: " + ", ".join(response['securityIssues']['unusedIAMUsers']['itemList']) + "\n"
            recon = True

        if response['securityIssues']['publicRWS3Buckets']['count']:
            speech_output += str(response['securityIssues']['publicRWS3Buckets']['count']) + " S3 buckes has public internet access. I strongly recommend you to harden bucket policy. If your content require internet user access then you can use Cloudfront with origin protection, signed URL or HTTP header referer for restricted s3 bucket access. "
            card_body += "S3 bucket with insecure read/write access: " + ", ".join(response['securityIssues']['publicRWS3Buckets']['itemList']) + "\n"
            recon = True

        if response['securityIssues']['insecurePublicPortsSGs']['count']:
            speech_output += "There are " + str(
                response['securityIssues']['insecurePublicPortsSGs']['count']) + " security group is having unsecure access for common vulnerable ports. "
            card_body += "Vulnerable security group ports (MSSQL, RDP, MySQL, FTP, Telnet) to internet: " + ",".join(
                response['securityIssues']['insecurePublicPortsSGs']['itemList']) + "\n"
            recon = True

        if response['securityIssues']['publicSSHAccess']['count']:
            speech_output += str(response['securityIssues']['publicSSHAccess']['count']) + " security group configured with port 22 open to internet. please close it as soon as possible. You should use AWS systems manager or use bastion host for any OS level administration. "
            card_body += "SSH port issue: " + ",".join(response['securityIssues']['publicSSHAccess']['itemList']) + "\n"

        if response['securityIssues']['publicRDS']['count']:
            speech_output += str(response['securityIssues']['publicRDS']['count']) + " Relational database instances found with public access enabled. Its highly recommended to disable the same. "
            card_body += "RDS database with public Access: " + ", ".join(response['securityIssues']['itemList']['count']) + "\n"
            recon = True

        if response['securityIssues']['cloudTrailsNotConfigured']['count']:
            speech_output += " Cloudtrail is also not enabled so auditing and tracing AWS infrastructure access will be difficult. I suggest you to enable it as soon as possible. "
            recon = True

        if response['securityIssues']['rdsDataEncryptionAtRest']['count']:
            speech_output += str(response['securityIssues']['rdsDataEncryptionAtRest']['count']) + " Relational database instances found with public access enabled. Its highly recommended to disable the same. "
            card_body += "RDS database with public Access: " + ", ".join(response['securityIssues']['rdsDataEncryptionAtRest']['itemList']) + "\n"
            recon = True

        if response['securityIssues']['rootAccountWithoutMFA']['count']:
            speech_output += "I have also noticed that current root account is not configured with multi factor authentication. you should enable it as per the best practice. "
            recon = True

        if speech_output == "In my security analysis i have found that ":
            speech_output += " there are no security vulnerability identified. I am learning the integration with new security tolls such as OS level security harening, AWS guard duty, AWS inspector and Trendmicor deep security. stay tuned for more updates. "
        else:
            speech_output += " I have sent you the details of the same on Alexa App. "

        return speech_output, card_body
