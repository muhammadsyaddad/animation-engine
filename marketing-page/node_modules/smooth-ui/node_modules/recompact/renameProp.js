'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _omit = require('./utils/omit');

var _omit2 = _interopRequireDefault(_omit);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _mapProps = require('./mapProps');

var _mapProps2 = _interopRequireDefault(_mapProps);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Renames a single prop.
 *
 * @static
 * @category Higher-order-components
 * @param {String} oldName
 * @param {String} newName
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * renameProp('data', 'value')
 */
var renameProp = function renameProp(oldName, newName) {
  return (0, _mapProps2.default)(function (props) {
    var _extends2;

    return _extends({}, (0, _omit2.default)(props, [oldName]), (_extends2 = {}, _extends2[newName] = props[oldName], _extends2));
  });
};

exports.default = (0, _createHelper2.default)(renameProp, 'renameProp');