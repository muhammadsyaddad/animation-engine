'use strict';

exports.__esModule = true;

var _createEagerElementUtil = require('./utils/createEagerElementUtil');

var _createEagerElementUtil2 = _interopRequireDefault(_createEagerElementUtil);

var _isReferentiallyTransparentFunctionComponent = require('./isReferentiallyTransparentFunctionComponent');

var _isReferentiallyTransparentFunctionComponent2 = _interopRequireDefault(_isReferentiallyTransparentFunctionComponent);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * React elements are lazily evaluated. But when a higher-order component
 * renders a functional component, the laziness doesn't have any real benefit.
 * createEagerElement() is a replacement for React.createElement() that checks
 * if the given component is referentially transparent. If so, rather than
 * returning a React element, it calls the functional component with the given
 * props and returns its output.
 *
 * @static
 * @category Utilities
 * @param {ReactClass|ReactFunctionalComponent|String} type The type of component to render.
 * @param {Object} [props] The props of the component.
 * @param {ReactNode} [children] The children of the component.
 * @returns {ReactElement} Returns a element.
 * @example
 *
 * createEagerElement('div', {className: 'foo'});
 */
var createEagerElement = function createEagerElement(type, props, children) {
  var isReferentiallyTransparent = (0, _isReferentiallyTransparentFunctionComponent2.default)(type);
  var hasKey = props && Object.prototype.hasOwnProperty.call(props, 'key');
  return (0, _createEagerElementUtil2.default)(hasKey, isReferentiallyTransparent, type, props, children);
};

exports.default = createEagerElement;