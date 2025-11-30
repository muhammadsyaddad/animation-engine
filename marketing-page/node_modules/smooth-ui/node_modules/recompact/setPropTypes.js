'use strict';

exports.__esModule = true;

var _setStatic = require('./setStatic');

var _setStatic2 = _interopRequireDefault(_setStatic);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Assigns to the `propTypes` property on the base component.
 *
 * @static
 * @category Higher-order-components
 * @param {Object} propTypes
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * setPropTypes({children: PropTypes.node})(MyComponent);
 */
var setPropTypes = function setPropTypes(propTypes) {
  return (0, _setStatic2.default)('propTypes', propTypes);
};

exports.default = setPropTypes;