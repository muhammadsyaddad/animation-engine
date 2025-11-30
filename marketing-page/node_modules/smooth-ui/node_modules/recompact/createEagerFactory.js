'use strict';

exports.__esModule = true;

var _createEagerElementUtil = require('./utils/createEagerElementUtil');

var _createEagerElementUtil2 = _interopRequireDefault(_createEagerElementUtil);

var _isReferentiallyTransparentFunctionComponent = require('./isReferentiallyTransparentFunctionComponent');

var _isReferentiallyTransparentFunctionComponent2 = _interopRequireDefault(_isReferentiallyTransparentFunctionComponent);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * The factory form of `createEagerElement()`.
 * Given a component, it returns a [factory](https://facebook.github.io/react/docs/react-api.html#createfactory).
 *
 * @static
 * @category Utilities
 * @param {ReactClass|ReactFunctionalComponent|String} type The type of component to render.
 * @returns {Function} Returns a function that take two arguments (props, children) and create
 * an element of the given type.
 * @example
 *
 * const div = createFactory('div');
 * div({className: 'foo'});
 */
var createEagerFactory = function createEagerFactory(type) {
  var isReferentiallyTransparent = (0, _isReferentiallyTransparentFunctionComponent2.default)(type);
  return function (props, children) {
    return (0, _createEagerElementUtil2.default)(false, isReferentiallyTransparent, type, props, children);
  };
};

exports.default = createEagerFactory;