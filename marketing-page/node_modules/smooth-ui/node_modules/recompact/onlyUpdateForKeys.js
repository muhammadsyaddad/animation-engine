'use strict';

exports.__esModule = true;

var _pick = require('./utils/pick');

var _pick2 = _interopRequireDefault(_pick);

var _shallowEqual = require('./shallowEqual');

var _shallowEqual2 = _interopRequireDefault(_shallowEqual);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _shouldUpdate = require('./shouldUpdate');

var _shouldUpdate2 = _interopRequireDefault(_shouldUpdate);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Prevents the component from updating unless a prop corresponding to one of the
 * given keys has updated. Uses `shallowEqual()` to test for changes.
 *
 * This is a much better optimization than the popular approach of using PureRenderMixin,
 * `shouldPureComponentUpdate()`, or `pure()` helper, because those
 * tools compare *every* prop, whereas `onlyUpdateForKeys()` only cares about the
 * props that you specify.
 *
 * @static
 * @category Higher-order-components
 * @param {String[]} propKeys The property keys that will induce a re-render.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @see shouldUpdate
 * @example
 *
 * onlyUpdateForKeys(['value'])
 */
var onlyUpdateForKeys = function onlyUpdateForKeys(propKeys) {
  return (0, _shouldUpdate2.default)(function (props, nextProps) {
    return !(0, _shallowEqual2.default)((0, _pick2.default)(nextProps, propKeys), (0, _pick2.default)(props, propKeys));
  });
};

exports.default = (0, _createHelper2.default)(onlyUpdateForKeys, 'onlyUpdateForKeys');