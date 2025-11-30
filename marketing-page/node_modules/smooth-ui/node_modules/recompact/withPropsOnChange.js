'use strict';

exports.__esModule = true;

var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

var _react = require('react');

var _pick = require('./utils/pick');

var _pick2 = _interopRequireDefault(_pick);

var _shallowEqual = require('./shallowEqual');

var _shallowEqual2 = _interopRequireDefault(_shallowEqual);

var _createHelper = require('./createHelper');

var _createHelper2 = _interopRequireDefault(_createHelper);

var _createEagerFactory = require('./createEagerFactory');

var _createEagerFactory2 = _interopRequireDefault(_createEagerFactory);

var _createCompactableHOC = require('./utils/createCompactableHOC');

var _createCompactableHOC2 = _interopRequireDefault(_createCompactableHOC);

var _updateProps = require('./utils/updateProps');

var _updateProps2 = _interopRequireDefault(_updateProps);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; }

/**
 * Like `withProps()`, except the new props are only created when one of the owner
 * props specified by `shouldMapOrKeys` changes. This helps ensure that expensive
 * computations inside `createProps()` are only executed when necessary.
 *
 * Instead of an array of prop keys, the first parameter can also be a function
 * that returns a boolean, given the current props and the next props. This allows
 * you to customize when `createProps()` should be called.
 *
 * @static
 * @category Higher-order-components
 * @param {Function|String|String[]} shouldMapOrKeys
 * @param {Function} createProps
 * @returns {HigherOrderComponent} A function that takes a component and returns a new component.
 * @example
 *
 * const withEmptyProp = withPropsOnChange('count', ({count}) => ({empty: count === 0}));
 */
var withPropsOnChange = function withPropsOnChange(shouldMapOrKeys, propsMapper) {
  var shouldMap = typeof shouldMapOrKeys === 'function' ? shouldMapOrKeys : function (props, nextProps) {
    return !(0, _shallowEqual2.default)((0, _pick2.default)(props, shouldMapOrKeys), (0, _pick2.default)(nextProps, shouldMapOrKeys));
  };

  return (0, _createCompactableHOC2.default)((0, _updateProps2.default)(function (next) {
    var props = {};
    var computedProps = void 0;

    return function (nextProps) {
      if (shouldMap(props, nextProps)) {
        computedProps = propsMapper(nextProps);
      }

      props = nextProps;
      next(_extends({}, nextProps, computedProps));
    };
  }), function (BaseComponent) {
    var factory = (0, _createEagerFactory2.default)(BaseComponent);

    return function (_Component) {
      _inherits(_class2, _Component);

      function _class2() {
        var _temp, _this, _ret;

        _classCallCheck(this, _class2);

        for (var _len = arguments.length, args = Array(_len), _key = 0; _key < _len; _key++) {
          args[_key] = arguments[_key];
        }

        return _ret = (_temp = (_this = _possibleConstructorReturn(this, _Component.call.apply(_Component, [this].concat(args))), _this), _this.computedProps = propsMapper(_this.props), _temp), _possibleConstructorReturn(_this, _ret);
      }

      _class2.prototype.componentWillReceiveProps = function componentWillReceiveProps(nextProps) {
        if (shouldMap(this.props, nextProps)) {
          this.computedProps = propsMapper(nextProps);
        }
      };

      _class2.prototype.render = function render() {
        return factory(_extends({}, this.props, this.computedProps));
      };

      return _class2;
    }(_react.Component);
  });
};

exports.default = (0, _createHelper2.default)(withPropsOnChange, 'withPropsOnChange');