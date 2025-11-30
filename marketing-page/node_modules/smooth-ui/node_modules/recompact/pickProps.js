'use strict';

exports.__esModule = true;

var _pick = require('./utils/pick');

var _pick2 = _interopRequireDefault(_pick);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _mapProps = require('./mapProps');

var _mapProps2 = _interopRequireDefault(_mapProps);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Same as lodash `pick` but for props.
 *
 * @static
 * @category Higher-order-components
 * @param {String|String[]} paths The property paths to pick.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @see https://lodash.com/docs/master#pick
 * @example
 *
 * const onlyWithValue = pickProps('value');
 */
var pickProps = function pickProps(paths) {
  return (0, _mapProps2.default)(function (props) {
    return (0, _pick2.default)(props, paths);
  });
};

exports.default = (0, _createHelper2.default)(pickProps, 'pickProps');