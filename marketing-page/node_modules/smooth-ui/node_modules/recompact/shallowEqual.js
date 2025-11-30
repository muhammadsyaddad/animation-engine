'use strict';

exports.__esModule = true;

var _shallowEqual = require('fbjs/lib/shallowEqual');

var _shallowEqual2 = _interopRequireDefault(_shallowEqual);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Returns true if objects are shallowly equal.
 *
 * @static
 * @category Utilities
 * @param {Object} a
 * @param {Object} b
 * @returns {Boolean}
 * @example
 *
 * shallowEqual({foo: 'bar'}, {foo: 'bar'}); // true
 * shallowEqual({foo: 'bar'}, {foo: 'x'}); // false
 */
exports.default = _shallowEqual2.default;