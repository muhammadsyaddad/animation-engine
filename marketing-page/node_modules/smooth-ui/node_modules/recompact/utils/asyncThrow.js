"use strict";

exports.__esModule = true;
exports.default = asyncThrow;
function asyncThrow(errorOrMessage) {
  var error = errorOrMessage instanceof Error ? errorOrMessage : new Error(errorOrMessage);
  setTimeout(function () {
    throw error;
  });
}