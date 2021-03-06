// Code generated by MockGen. DO NOT EDIT.
// Source: github.com/scionproto/scion/go/cs/keepalive (interfaces: IfStatePusher,RevDropper)

// Package mock_keepalive is a generated GoMock package.
package mock_keepalive

import (
	context "context"
	gomock "github.com/golang/mock/gomock"
	addr "github.com/scionproto/scion/go/lib/addr"
	common "github.com/scionproto/scion/go/lib/common"
	reflect "reflect"
)

// MockIfStatePusher is a mock of IfStatePusher interface
type MockIfStatePusher struct {
	ctrl     *gomock.Controller
	recorder *MockIfStatePusherMockRecorder
}

// MockIfStatePusherMockRecorder is the mock recorder for MockIfStatePusher
type MockIfStatePusherMockRecorder struct {
	mock *MockIfStatePusher
}

// NewMockIfStatePusher creates a new mock instance
func NewMockIfStatePusher(ctrl *gomock.Controller) *MockIfStatePusher {
	mock := &MockIfStatePusher{ctrl: ctrl}
	mock.recorder = &MockIfStatePusherMockRecorder{mock}
	return mock
}

// EXPECT returns an object that allows the caller to indicate expected use
func (m *MockIfStatePusher) EXPECT() *MockIfStatePusherMockRecorder {
	return m.recorder
}

// Push mocks base method
func (m *MockIfStatePusher) Push(arg0 context.Context, arg1 common.IFIDType) {
	m.ctrl.T.Helper()
	m.ctrl.Call(m, "Push", arg0, arg1)
}

// Push indicates an expected call of Push
func (mr *MockIfStatePusherMockRecorder) Push(arg0, arg1 interface{}) *gomock.Call {
	mr.mock.ctrl.T.Helper()
	return mr.mock.ctrl.RecordCallWithMethodType(mr.mock, "Push", reflect.TypeOf((*MockIfStatePusher)(nil).Push), arg0, arg1)
}

// MockRevDropper is a mock of RevDropper interface
type MockRevDropper struct {
	ctrl     *gomock.Controller
	recorder *MockRevDropperMockRecorder
}

// MockRevDropperMockRecorder is the mock recorder for MockRevDropper
type MockRevDropperMockRecorder struct {
	mock *MockRevDropper
}

// NewMockRevDropper creates a new mock instance
func NewMockRevDropper(ctrl *gomock.Controller) *MockRevDropper {
	mock := &MockRevDropper{ctrl: ctrl}
	mock.recorder = &MockRevDropperMockRecorder{mock}
	return mock
}

// EXPECT returns an object that allows the caller to indicate expected use
func (m *MockRevDropper) EXPECT() *MockRevDropperMockRecorder {
	return m.recorder
}

// DeleteRevocation mocks base method
func (m *MockRevDropper) DeleteRevocation(arg0 context.Context, arg1 addr.IA, arg2 common.IFIDType) error {
	m.ctrl.T.Helper()
	ret := m.ctrl.Call(m, "DeleteRevocation", arg0, arg1, arg2)
	ret0, _ := ret[0].(error)
	return ret0
}

// DeleteRevocation indicates an expected call of DeleteRevocation
func (mr *MockRevDropperMockRecorder) DeleteRevocation(arg0, arg1, arg2 interface{}) *gomock.Call {
	mr.mock.ctrl.T.Helper()
	return mr.mock.ctrl.RecordCallWithMethodType(mr.mock, "DeleteRevocation", reflect.TypeOf((*MockRevDropper)(nil).DeleteRevocation), arg0, arg1, arg2)
}
