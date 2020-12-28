class Utilities{
    constructor() {
    }

    static randomString(length) {        
        var result = '';
        var chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
        for (var i = length; i > 0; --i) result += chars[Math.floor(Math.random() * chars.length)];
        return result;
    }
    static buildResponse(code, body){
        const response = {
            statusCode: code,
            body: JSON.stringify(body),
            headers: {'Access-Control-Allow-Origin': '*'}
        };
        return response;
    }
    static table(tableName){
      if(process.env.STAGE) {
        return process.env.STAGE+'_'+tableName;
      }
      return tableName;
    }

    static groupBy(array, property){
      return array.reduce(function(groups, item) {
          const val = item[property]
          groups[val] = groups[val] || []
          groups[val].push(item)
          return groups
        }, {})
    }
    static timestamp(){
      return new Date().toISOString()      
    }
}

module.exports = Utilities