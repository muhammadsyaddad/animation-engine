'use strict';

exports.__esModule = true;

var _setStatic = require('./setStatic');

var _setStatic2 = _interopRequireDefault(_setStatic);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Assigns to the `displayName` property on the base component.
 *
 * @static
 * @category Higher-order-components
 * @param {String} displayName
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * setDisplayName('AnotherDisplayName')(MyComponent);
 */
var setDisplayName = function setDisplayName(displayName) {
  return (0, _setStatic2.default)('displayName', displayName);
};

exports.default = setDisplayName;