'use strict';

exports.__esModule = true;

var _createHOCFromMapper = require('./createHOCFromMapper');

var _WeakMap = require('./WeakMap');

var _WeakMap2 = _interopRequireDefault(_WeakMap);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

/* eslint-disable no-param-reassign */

var allCompactableComponents = new _WeakMap2.default();
var isCompactable = function isCompactable(Component) {
  return allCompactableComponents.has(Component);
};
var getCompactableComponent = function getCompactableComponent(Component) {
  return allCompactableComponents.get(Component);
};
var setCompactableComponent = function setCompactableComponent(Component, CompactableComponent) {
  return allCompactableComponents.set(Component, CompactableComponent);
};

exports.default = function (createCompactableComponent, createComponent) {
  return function (BaseComponent) {
    if (isCompactable(BaseComponent)) {
      BaseComponent = getCompactableComponent(BaseComponent);
    }

    var Component = createComponent(BaseComponent);
    setCompactableComponent(Component, createCompactableComponent(BaseComponent));

    if ((0, _createHOCFromMapper.isMapperComponent)(BaseComponent)) {
      return getCompactableComponent(Component);
    }

    return Component;
  };
};