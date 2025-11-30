'use strict';

exports.__esModule = true;

exports.default = function (fnOrObject, a, b, c) {
  return typeof fnOrObject === 'function' ? fnOrObject(a, b, c) : fnOrObject;
};