'use strict';

exports.__esModule = true;

var _typeof = typeof Symbol === "function" && typeof Symbol.iterator === "symbol" ? function (obj) { return typeof obj; } : function (obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; };

/**
 * Returns true if the given value is a React component class.
 *
 * @static
 * @category Utilities
 * @param {*} value Any value
 * @returns {Boolean} Returns true if the given value is a React component class.
 * @see https://lodash.com/docs/master#identity
 * @example
 *
 * const Nothing = () => null;
 * const Nothing2 = class extends Component { render() { return null; } };
 * const Nothing3 = React.createClass({ render() { return null; } });
 * isClassComponent(Nothing); // false
 * isClassComponent(Nothing2); // true
 * isClassComponent(Nothing3); // true
 */
var isClassComponent = function isClassComponent(Component) {
  return Boolean(Component && Component.prototype && _typeof(Component.prototype.isReactComponent) === 'object');
};

exports.default = isClassComponent;