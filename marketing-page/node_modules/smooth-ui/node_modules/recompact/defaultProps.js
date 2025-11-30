'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; }; /* eslint-disable no-shadow, no-restricted-syntax, no-param-reassign */


var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _createEagerFactory = require('./createEagerFactory');

var _createEagerFactory2 = _interopRequireDefault(_createEagerFactory);

var _mapProps = require('./mapProps');

var _mapProps2 = _interopRequireDefault(_mapProps);

var _createCompactableHOC = require('./utils/createCompactableHOC');

var _createCompactableHOC2 = _interopRequireDefault(_createCompactableHOC);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Specify props values that will be used if the prop is `undefined`.
 *
 * @static
 * @category Higher-order-components
 * @param {Object} defaultProps Default props.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * const Button = defaultProps({type: 'button'})('button');
 * <Button /> // will render <button type="button" />
 */
var defaultProps = function defaultProps(_defaultProps) {
  return (0, _createCompactableHOC2.default)((0, _mapProps2.default)(function (props) {
    var newProps = {};
    var propKeys = Object.keys(_defaultProps);
    for (var i = 0; i < propKeys.length; i += 1) {
      var propKey = propKeys[i];
      if (props[propKey] === undefined) {
        newProps[propKey] = _defaultProps[propKey];
      }
    }
    return _extends({}, props, newProps);
  }), function (BaseComponent) {
    var factory = (0, _createEagerFactory2.default)(BaseComponent);
    var DefaultProps = function DefaultProps(ownerProps) {
      return factory(ownerProps);
    };
    DefaultProps.defaultProps = _defaultProps;
    return DefaultProps;
  });
};

exports.default = (0, _createHelper2.default)(defaultProps, 'defaultProps');