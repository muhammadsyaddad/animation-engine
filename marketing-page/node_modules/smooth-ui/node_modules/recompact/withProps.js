'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _callOrUse = require('./utils/callOrUse');

var _callOrUse2 = _interopRequireDefault(_callOrUse);

var _createEagerFactory = require('./createEagerFactory');

var _createEagerFactory2 = _interopRequireDefault(_createEagerFactory);

var _createCompactableHOC = require('./utils/createCompactableHOC');

var _createCompactableHOC2 = _interopRequireDefault(_createCompactableHOC);

var _updateProps = require('./utils/updateProps');

var _updateProps2 = _interopRequireDefault(_updateProps);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Like `mapProps()`, except the newly created props are merged with the owner props.
 *
 * Instead of a function, you can also pass a props object directly. In this form,
 * it is similar to `defaultProps()`, except the provided props take precedence over
 * props from the owner.
 *
 * @static
 * @category Higher-order-components
 * @param {Function|Object} propsMapper
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * const Button = withProps({type: 'button'})('button');
 * const XButton = withProps(({type}) => {type: `x${type}`})('button');
 */
var withProps = function withProps(propsMapper) {
  return (0, _createCompactableHOC2.default)((0, _updateProps2.default)(function (next) {
    return function (props) {
      next(_extends({}, props, (0, _callOrUse2.default)(propsMapper, props)));
    };
  }), function (BaseComponent) {
    var factory = (0, _createEagerFactory2.default)(BaseComponent);
    return function (props) {
      return factory(_extends({}, props, (0, _callOrUse2.default)(propsMapper, props)));
    };
  });
};

exports.default = (0, _createHelper2.default)(withProps, 'withProps');