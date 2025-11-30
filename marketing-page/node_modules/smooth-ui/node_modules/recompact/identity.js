"use strict";

exports.__esModule = true;
/**
 * This method is similar to lodash `identity`. It returns the first argument it receives.
 *
 * @static
 * @category Utilities
 * @param {*} value Any value
 * @returns {*} Returns `value`
 * @see https://lodash.com/docs/master#identity
 * @example
 *
 * identity(Component) === Component
 */
var identity = function identity(x) {
  return x;
};

exports.default = identity;