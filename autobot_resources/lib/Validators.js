class Validators{
  constructor() {}
  static isEmailValid(email){
    return /(.+)@(.+){2,}\.(.+){2,}/.test(email);
  }
}

module.exports = Validators;