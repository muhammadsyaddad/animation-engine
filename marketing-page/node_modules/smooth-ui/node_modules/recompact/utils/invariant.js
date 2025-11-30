"use strict";

exports.__esModule = true;

exports.default = function (condition, message) {
  if (!condition) throw new Error(message);
};