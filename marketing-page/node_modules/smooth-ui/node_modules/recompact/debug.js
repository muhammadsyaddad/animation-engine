'use strict';

exports.__esModule = true;

var _createEagerFactory = require('./createEagerFactory');

var _createEagerFactory2 = _interopRequireDefault(_createEagerFactory);

var _getDisplayName = require('./getDisplayName');

var _getDisplayName2 = _interopRequireDefault(_getDisplayName);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Display the flow of props.
 * Very useful for debugging higher-order component stack.
 *
 * @static
 * @category Higher-order-components
 * @param {*} label A label displayed in console.
 * @param {Function} selector A props selector.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * recompact.compose(
 *   recompact.withProps({ foo: 'bar' }),
 *   recompact.debug(),
 *   recompact.renameProp('foo', 'className'),
 *   recompact.debug(),
 * )('input')
 */
/* eslint-disable no-param-reassign, no-console */
var debug = function debug(label) {
  var selector = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : function (x) {
    return x;
  };
  return function (BaseComponent) {
    var factory = (0, _createEagerFactory2.default)(BaseComponent);
    label = label || (0, _getDisplayName2.default)(BaseComponent);
    return function (props) {
      console.log(label, selector(props));
      return factory(props);
    };
  };
};

exports.default = debug;