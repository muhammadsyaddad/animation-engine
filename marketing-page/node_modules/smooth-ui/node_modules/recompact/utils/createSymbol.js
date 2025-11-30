'use strict';

exports.__esModule = true;

exports.default = function (name) {
  return typeof Symbol === 'function' ? Symbol(name) : '@@recompact/' + name;
};