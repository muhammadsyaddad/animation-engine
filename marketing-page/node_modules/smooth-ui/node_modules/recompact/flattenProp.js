'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _warning = require('warning');

var _warning2 = _interopRequireDefault(_warning);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _mapProps = require('./mapProps');

var _mapProps2 = _interopRequireDefault(_mapProps);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Flattens a prop so that its fields are spread out into the props object.
 *
 * @static
 * @category Higher-order-components
 * @deprecated since v3.0.0, use flattenProps instead
 * @param {String} propName Name of the prop to flatten.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * const Button = flattenProp('props')('button');
 * <Button props={{type: 'submit'}} /> // will render <button type="submit" />
 */
var flattenProp = function flattenProp(propName) {
  if (process.env.NODE_ENV !== 'production') {
    (0, _warning2.default)(true, '`flattenProp` is deprecated, please use `flattenProps` instead.');
  }

  return (0, _mapProps2.default)(function (props) {
    return _extends({}, props, props[propName]);
  });
};

exports.default = (0, _createHelper2.default)(flattenProp, 'flattenProp');