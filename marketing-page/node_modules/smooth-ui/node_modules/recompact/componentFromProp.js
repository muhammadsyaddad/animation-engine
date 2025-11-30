'use strict';

exports.__esModule = true;

var _omit = require('./utils/omit');

var _omit2 = _interopRequireDefault(_omit);

var _createEagerElement = require('./createEagerElement');

var _createEagerElement2 = _interopRequireDefault(_createEagerElement);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/**
 * Creates a component that accepts a component as a prop and renders it
 * with the remaining props.
 *
 * @static
 * @category Utilities
 * @param {String} prop The prop to render as Component.
 * @returns {ReactFunctionalComponent} Returns a Component.
 * @example
 *
 * const enhance = defaultProps({component: 'button'});
 * const Button = enhance(componentFromProp('component'));
 *
 * <Button foo="bar" /> // renders <button foo="bar" />
 * <Button component="a" foo="bar" />  // renders <a foo="bar" />
 * <Button component={Link} foo="bar" />  // renders <Link foo="bar" />
 */
var componentFromProp = function componentFromProp(propName) {
  var Component = function Component(props) {
    return (0, _createEagerElement2.default)(props[propName], (0, _omit2.default)(props, [propName]));
  };

  if (process.env.NODE_ENV !== 'production') {
    Component.displayName = 'componentFromProp(' + propName + ')';
  }

  return Component;
};

exports.default = componentFromProp;