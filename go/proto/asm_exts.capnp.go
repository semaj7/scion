// Code generated by capnpc-go. DO NOT EDIT.

package proto

import (
	capnp "zombiezen.com/go/capnproto2"
	text "zombiezen.com/go/capnproto2/encoding/text"
	schemas "zombiezen.com/go/capnproto2/schemas"
)

type RoutingPolicyExt struct{ capnp.Struct }

// RoutingPolicyExt_TypeID is the unique identifier for the type RoutingPolicyExt.
const RoutingPolicyExt_TypeID = 0x96c1dab83835e4f9

func NewRoutingPolicyExt(s *capnp.Segment) (RoutingPolicyExt, error) {
	st, err := capnp.NewStruct(s, capnp.ObjectSize{DataSize: 16, PointerCount: 1})
	return RoutingPolicyExt{st}, err
}

func NewRootRoutingPolicyExt(s *capnp.Segment) (RoutingPolicyExt, error) {
	st, err := capnp.NewRootStruct(s, capnp.ObjectSize{DataSize: 16, PointerCount: 1})
	return RoutingPolicyExt{st}, err
}

func ReadRootRoutingPolicyExt(msg *capnp.Message) (RoutingPolicyExt, error) {
	root, err := msg.RootPtr()
	return RoutingPolicyExt{root.Struct()}, err
}

func (s RoutingPolicyExt) String() string {
	str, _ := text.Marshal(0x96c1dab83835e4f9, s.Struct)
	return str
}

func (s RoutingPolicyExt) Set() bool {
	return s.Struct.Bit(0)
}

func (s RoutingPolicyExt) SetSet(v bool) {
	s.Struct.SetBit(0, v)
}

func (s RoutingPolicyExt) PolType() uint8 {
	return s.Struct.Uint8(1)
}

func (s RoutingPolicyExt) SetPolType(v uint8) {
	s.Struct.SetUint8(1, v)
}

func (s RoutingPolicyExt) IfID() uint64 {
	return s.Struct.Uint64(8)
}

func (s RoutingPolicyExt) SetIfID(v uint64) {
	s.Struct.SetUint64(8, v)
}

func (s RoutingPolicyExt) Isdases() (capnp.UInt64List, error) {
	p, err := s.Struct.Ptr(0)
	return capnp.UInt64List{List: p.List()}, err
}

func (s RoutingPolicyExt) HasIsdases() bool {
	p, err := s.Struct.Ptr(0)
	return p.IsValid() || err != nil
}

func (s RoutingPolicyExt) SetIsdases(v capnp.UInt64List) error {
	return s.Struct.SetPtr(0, v.List.ToPtr())
}

// NewIsdases sets the isdases field to a newly
// allocated capnp.UInt64List, preferring placement in s's segment.
func (s RoutingPolicyExt) NewIsdases(n int32) (capnp.UInt64List, error) {
	l, err := capnp.NewUInt64List(s.Struct.Segment(), n)
	if err != nil {
		return capnp.UInt64List{}, err
	}
	err = s.Struct.SetPtr(0, l.List.ToPtr())
	return l, err
}

// RoutingPolicyExt_List is a list of RoutingPolicyExt.
type RoutingPolicyExt_List struct{ capnp.List }

// NewRoutingPolicyExt creates a new list of RoutingPolicyExt.
func NewRoutingPolicyExt_List(s *capnp.Segment, sz int32) (RoutingPolicyExt_List, error) {
	l, err := capnp.NewCompositeList(s, capnp.ObjectSize{DataSize: 16, PointerCount: 1}, sz)
	return RoutingPolicyExt_List{l}, err
}

func (s RoutingPolicyExt_List) At(i int) RoutingPolicyExt { return RoutingPolicyExt{s.List.Struct(i)} }

func (s RoutingPolicyExt_List) Set(i int, v RoutingPolicyExt) error {
	return s.List.SetStruct(i, v.Struct)
}

func (s RoutingPolicyExt_List) String() string {
	str, _ := text.MarshalList(0x96c1dab83835e4f9, s.List)
	return str
}

// RoutingPolicyExt_Promise is a wrapper for a RoutingPolicyExt promised by a client call.
type RoutingPolicyExt_Promise struct{ *capnp.Pipeline }

func (p RoutingPolicyExt_Promise) Struct() (RoutingPolicyExt, error) {
	s, err := p.Pipeline.Struct()
	return RoutingPolicyExt{s}, err
}

type ISDAnnouncementExt struct{ capnp.Struct }

// ISDAnnouncementExt_TypeID is the unique identifier for the type ISDAnnouncementExt.
const ISDAnnouncementExt_TypeID = 0xc586650e812cc6a1

func NewISDAnnouncementExt(s *capnp.Segment) (ISDAnnouncementExt, error) {
	st, err := capnp.NewStruct(s, capnp.ObjectSize{DataSize: 8, PointerCount: 0})
	return ISDAnnouncementExt{st}, err
}

func NewRootISDAnnouncementExt(s *capnp.Segment) (ISDAnnouncementExt, error) {
	st, err := capnp.NewRootStruct(s, capnp.ObjectSize{DataSize: 8, PointerCount: 0})
	return ISDAnnouncementExt{st}, err
}

func ReadRootISDAnnouncementExt(msg *capnp.Message) (ISDAnnouncementExt, error) {
	root, err := msg.RootPtr()
	return ISDAnnouncementExt{root.Struct()}, err
}

func (s ISDAnnouncementExt) String() string {
	str, _ := text.Marshal(0xc586650e812cc6a1, s.Struct)
	return str
}

func (s ISDAnnouncementExt) Set() bool {
	return s.Struct.Bit(0)
}

func (s ISDAnnouncementExt) SetSet(v bool) {
	s.Struct.SetBit(0, v)
}

// ISDAnnouncementExt_List is a list of ISDAnnouncementExt.
type ISDAnnouncementExt_List struct{ capnp.List }

// NewISDAnnouncementExt creates a new list of ISDAnnouncementExt.
func NewISDAnnouncementExt_List(s *capnp.Segment, sz int32) (ISDAnnouncementExt_List, error) {
	l, err := capnp.NewCompositeList(s, capnp.ObjectSize{DataSize: 8, PointerCount: 0}, sz)
	return ISDAnnouncementExt_List{l}, err
}

func (s ISDAnnouncementExt_List) At(i int) ISDAnnouncementExt {
	return ISDAnnouncementExt{s.List.Struct(i)}
}

func (s ISDAnnouncementExt_List) Set(i int, v ISDAnnouncementExt) error {
	return s.List.SetStruct(i, v.Struct)
}

func (s ISDAnnouncementExt_List) String() string {
	str, _ := text.MarshalList(0xc586650e812cc6a1, s.List)
	return str
}

// ISDAnnouncementExt_Promise is a wrapper for a ISDAnnouncementExt promised by a client call.
type ISDAnnouncementExt_Promise struct{ *capnp.Pipeline }

func (p ISDAnnouncementExt_Promise) Struct() (ISDAnnouncementExt, error) {
	s, err := p.Pipeline.Struct()
	return ISDAnnouncementExt{s}, err
}

type HiddenPathSegExtn struct{ capnp.Struct }

// HiddenPathSegExtn_TypeID is the unique identifier for the type HiddenPathSegExtn.
const HiddenPathSegExtn_TypeID = 0xff79b399e1e58cf3

func NewHiddenPathSegExtn(s *capnp.Segment) (HiddenPathSegExtn, error) {
	st, err := capnp.NewStruct(s, capnp.ObjectSize{DataSize: 8, PointerCount: 0})
	return HiddenPathSegExtn{st}, err
}

func NewRootHiddenPathSegExtn(s *capnp.Segment) (HiddenPathSegExtn, error) {
	st, err := capnp.NewRootStruct(s, capnp.ObjectSize{DataSize: 8, PointerCount: 0})
	return HiddenPathSegExtn{st}, err
}

func ReadRootHiddenPathSegExtn(msg *capnp.Message) (HiddenPathSegExtn, error) {
	root, err := msg.RootPtr()
	return HiddenPathSegExtn{root.Struct()}, err
}

func (s HiddenPathSegExtn) String() string {
	str, _ := text.Marshal(0xff79b399e1e58cf3, s.Struct)
	return str
}

func (s HiddenPathSegExtn) Set() bool {
	return s.Struct.Bit(0)
}

func (s HiddenPathSegExtn) SetSet(v bool) {
	s.Struct.SetBit(0, v)
}

// HiddenPathSegExtn_List is a list of HiddenPathSegExtn.
type HiddenPathSegExtn_List struct{ capnp.List }

// NewHiddenPathSegExtn creates a new list of HiddenPathSegExtn.
func NewHiddenPathSegExtn_List(s *capnp.Segment, sz int32) (HiddenPathSegExtn_List, error) {
	l, err := capnp.NewCompositeList(s, capnp.ObjectSize{DataSize: 8, PointerCount: 0}, sz)
	return HiddenPathSegExtn_List{l}, err
}

func (s HiddenPathSegExtn_List) At(i int) HiddenPathSegExtn {
	return HiddenPathSegExtn{s.List.Struct(i)}
}

func (s HiddenPathSegExtn_List) Set(i int, v HiddenPathSegExtn) error {
	return s.List.SetStruct(i, v.Struct)
}

func (s HiddenPathSegExtn_List) String() string {
	str, _ := text.MarshalList(0xff79b399e1e58cf3, s.List)
	return str
}

// HiddenPathSegExtn_Promise is a wrapper for a HiddenPathSegExtn promised by a client call.
type HiddenPathSegExtn_Promise struct{ *capnp.Pipeline }

func (p HiddenPathSegExtn_Promise) Struct() (HiddenPathSegExtn, error) {
	s, err := p.Pipeline.Struct()
	return HiddenPathSegExtn{s}, err
}

const schema_e6c88f91b6a1209e = "x\xda\x8c\xce?\x8b\x13A\x1c\xc6\xf1\xe7\x99\xd9d\x8d" +
	"h\x925\xfb\x02\xc4RD\x08\"\x88\x8d\x7fH\xc0t" +
	";\xc6F\x10t\xc9\x8e\xc9Bvva'\xb0[\x05" +
	"A\xad\x04I\xa1b#\xe45\x08bk\xa1\xf8\x1a\xae" +
	";\xb8?/\xe0\xaa\xab\xf6\xd8\x14w\x1c\x97\xe2\xda\x1f" +
	"\x9fy\xe6\xdb\xfd\xf6X\xf4\x1b\x1d\x02\xeaZ\xa3Y\x1d" +
	"\xef\xdd\x7f\xf0{\xe7\xcfW\xa8\x0eE\xf5\xe3\xe6\xfa\xd7" +
	"\xea\xf3\xff\x034\xe8\x02\xfdD\xd0+]\xc0[\x1c\x82" +
	"\xd5\xfa\xdf\x9dwm\xfd\xf1oMyF\x1d\x17\xb8\xf7" +
	"\x927\xd8\x8b\xebG=\xcdG`u\xf4i\x7f\xf7\xfb" +
	"\xcf\xb2\xda\x86?\xf0*{_6x\xb5\xc1a\x9e\xbc" +
	"\xd6\x85\xcd\xe5\xddI\x98\x99\xec\xe1\xf3tac3\x0d" +
	"\xd2y<)\x87\x85E@\xaa\xaet\x00\x87\x80\x17\xde" +
	"\x02\xd4+I5\x13\xf4H\x9f\xf5Q?\x05\xd4\x1bI" +
	"5\x17\xf4\x04}\x0a\xc0\x8bo\x03*\x92T\x99 \xa5" +
	"O\x09xI\x0dg\x92\xea\xbd\xa0\x9bkKB\x90\xe0" +
	"2K\xe7/\xcaL\xb3\x09\xc1&\xd8\x89\xdf\x8e\x06l" +
	"A\xb0\x05.\xe3<\x0as\x9d\xb3\x0d\x06\x92\x9bs{" +
	"K\xf9h<xbL\xba0\x13\x9dhc\x87\x05m" +
	"\xdd\xee\x9c\xb6_\xaf\xdb\xafH*\xff\xfc\xef\x17\x96\x9e" +
	"\xc5Q\xa4M\x10\xda\xd9XO\x87\x855\xc0\xe5\x96N" +
	"\x02\x00\x00\xff\xff#\x1dpa"

func init() {
	schemas.Register(schema_e6c88f91b6a1209e,
		0x96c1dab83835e4f9,
		0xc586650e812cc6a1,
		0xff79b399e1e58cf3)
}
