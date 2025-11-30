'use strict';

exports.__esModule = true;

var _createHOCFromMapper = require('./utils/createHOCFromMapper');

var _createHOCFromMapper2 = _interopRequireDefault(_createHOCFromMapper);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Accepts a function that maps an observable stream of owner props to a stream
 * of child props, rather than directly to a stream of React nodes.
 * The child props are then passed to a base component.
 *
 * @static
 * @category Higher-order-components
 * @param {Function} propsStreamMapper
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * // Delay rendering of 1s
 * const delayRendering = mapPropsStream(props$ => props$.delay(1000));
 */
var mapPropsStream = function mapPropsStream(propsStreamMapper) {
  return (0, _createHOCFromMapper2.default)(function (props$, obs) {
    return [propsStreamMapper(props$), obs];
  });
};

exports.default = (0, _createHelper2.default)(mapPropsStream, 'mapPropsStream');