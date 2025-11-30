'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _mapProps = require('./mapProps');

var _mapProps2 = _interopRequireDefault(_mapProps);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Flattens one or several props so that its fields are spread out into the props object.
 *
 * @static
 * @category Higher-order-components
 * @alias flattenProp
 * @param {String|String[]} paths The property paths to flatten.
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * const Button = flattenProps(['a', 'b'])('button');
 * // Will render <button type="submit" className="btn" />
 * <Button a={{type: 'submit'}} b={{className: 'btn'}} />
 */
var flattenProps = function flattenProps(paths) {
  return (0, _mapProps2.default)(function (props) {
    if (typeof paths === 'string') {
      return _extends({}, props, props[paths]);
    }

    return paths.reduce(function (nextProps, path) {
      return _extends({}, nextProps, props[path]);
    }, props);
  });
};

exports.default = (0, _createHelper2.default)(flattenProps, 'flattenProps');