const AWS = require('aws-sdk');
const dynamoDb = new AWS.DynamoDB.DocumentClient();
const Validators = require('./Validators')
const Utilities = require('./Utilities')

class ContactInfo {    
    constructor(email, phone, name, message, identity) {
        this.email = email;
        this.phone = phone;
        this.name = name;
        this.message = message;
        this.identity = identity;
    }

    save() {
        if (!Validators.isEmailValid(this.email)) {
            return { success: false, error_message: "Email is Invalid", error_code: "CSP_EMAIL_INVALID" };
        }
        var id = Utilities.generateUUID();
        var datetime = new Date().toISOString();

        const params = {
            TableName: Utilities.table('contact_info'),
            Item: {
                id: id,
                email: this.email,
                phone: this.phone,
                name: this.name,
                message: this.message,
                identity: this.identity,
                createdAt: datetime                
            },
        };
        return dynamoDb.put(params).promise().then((result) => {
            this.id = id;
            return { success: true, contactInfoId: id};
        }).catch((error) => {
            console.error("Contact infor creation failed");
            console.error(error);
            return { success: false, error_message: "Clouldn't save ContactInfo", error_code: "CI_SAVE_FAILED" };
        });
    }   
}

module.exports = ContactInfo;
