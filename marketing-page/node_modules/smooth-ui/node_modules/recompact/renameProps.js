'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _omit = require('./utils/omit');

var _omit2 = _interopRequireDefault(_omit);

var _pick = require('./utils/pick');

var _pick2 = _interopRequireDefault(_pick);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _mapProps = require('./mapProps');

var _mapProps2 = _interopRequireDefault(_mapProps);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

var keys = Object.keys;


var mapKeys = function mapKeys(obj, func) {
  return keys(obj).reduce(function (result, key) {
    var val = obj[key];
    /* eslint-disable no-param-reassign */
    result[func(val, key)] = val;
    /* eslint-enable no-param-reassign */
    return result;
  }, {});
};

/**
 * Renames multiple props, using a map of old prop names to new prop names.
 *
 * @static
 * @category Higher-order-components
 * @param {Object} nameMap A map with old prop as key and new prop as value.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * renameProps({data: 'value'})
 */
var renameProps = function renameProps(nameMap) {
  return (0, _mapProps2.default)(function (props) {
    return _extends({}, (0, _omit2.default)(props, keys(nameMap)), mapKeys((0, _pick2.default)(props, keys(nameMap)), function (_, oldName) {
      return nameMap[oldName];
    }));
  });
};

exports.default = (0, _createHelper2.default)(renameProps, 'renameProps');