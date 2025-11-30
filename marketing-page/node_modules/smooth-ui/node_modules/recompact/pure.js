'use strict';

exports.__esModule = true;

var _shallowEqual = require('./shallowEqual');

var _shallowEqual2 = _interopRequireDefault(_shallowEqual);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _shouldUpdate = require('./shouldUpdate');

var _shouldUpdate2 = _interopRequireDefault(_shouldUpdate);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Prevents the component from updating unless a prop has changed.
 * Uses `shallowEqual()` to test for changes.
 *
 * @static
 * @category Higher-order-components
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * pure('button')
 */
var pure = (0, _shouldUpdate2.default)(function (props, nextProps) {
  return !(0, _shallowEqual2.default)(props, nextProps);
});

exports.default = (0, _createHelper2.default)(pure, 'pure', true, true);