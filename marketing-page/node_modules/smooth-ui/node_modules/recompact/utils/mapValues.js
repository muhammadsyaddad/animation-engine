"use strict";

exports.__esModule = true;

exports.default = function (obj, fn) {
  return Object.keys(obj).reduce(function (result, key) {
    result[key] = fn(obj[key], key); // eslint-disable-line no-param-reassign
    return result;
  }, {});
};