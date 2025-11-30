'use strict';

exports.__esModule = true;

var _omit = require('./utils/omit');

var _omit2 = _interopRequireDefault(_omit);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _mapProps = require('./mapProps');

var _mapProps2 = _interopRequireDefault(_mapProps);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Same as lodash `omit` but for props.
 *
 * @static
 * @category Higher-order-components
 * @param {String|String[]} paths The property paths to omit.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @see https://lodash.com/docs/master#omit
 * @example
 *
 * const withoutValue = omitProps('value');
 */
var omitProps = function omitProps(paths) {
  return (0, _mapProps2.default)(function (props) {
    return (0, _omit2.default)(props, paths);
  });
};

exports.default = (0, _createHelper2.default)(omitProps, 'omitProps');