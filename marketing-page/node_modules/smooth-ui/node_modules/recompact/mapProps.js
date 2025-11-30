'use strict';

exports.__esModule = true;

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _createEagerFactory = require('./createEagerFactory');

var _createEagerFactory2 = _interopRequireDefault(_createEagerFactory);

var _createCompactableHOC = require('./utils/createCompactableHOC');

var _createCompactableHOC2 = _interopRequireDefault(_createCompactableHOC);

var _updateProps = require('./utils/updateProps');

var _updateProps2 = _interopRequireDefault(_updateProps);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Accepts a function that maps owner props to a new collection of props that
 * are passed to the base component.
 *
 * @static
 * @category Higher-order-components
 * @param {Function} propsMapper The function that returns new props.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * // Add a new prop computed from owner props
 * mapProps(({count}) => ({moreThanFive: count > 5}))(MyComponent);
 */
var mapProps = function mapProps(propsMapper) {
  return (0, _createCompactableHOC2.default)((0, _updateProps2.default)(function (next) {
    return function (props) {
      next(propsMapper(props));
    };
  }), function (BaseComponent) {
    var factory = (0, _createEagerFactory2.default)(BaseComponent);
    return function (props) {
      return factory(propsMapper(props));
    };
  });
};

exports.default = (0, _createHelper2.default)(mapProps, 'mapProps');