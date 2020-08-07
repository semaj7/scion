package main

import (
	"fmt"
	"regexp"
	"strings"

	"github.com/scionproto/scion/go/lib/addr"
	"github.com/scionproto/scion/go/lib/common"
	"github.com/scionproto/scion/go/lib/snet"
)

type scionPathDescription struct {
	IAList []addr.IA
	IDList []common.IFIDType
}

func (spd *scionPathDescription) Set(input string) error {
	isdasidList := strings.Split(input, ">")
	spd.IAList = make([]addr.IA, 2*(len(isdasidList)-1))
	spd.IDList = make([]common.IFIDType, 2*(len(isdasidList)-1))
	reFirst := regexp.MustCompile(`^([^ ]*) (\d+)$`)
	reIntermediate := regexp.MustCompile(`^(\d+) ([^ ]*) (\d+)$`)
	reLast := regexp.MustCompile(`^(\d+) ([^ ]*)$`)
	if len(isdasidList) < 2 {
		return fmt.Errorf("Cannot parse path of length %d", len(isdasidList))
	}
	index := 0
	for i, iaidString := range isdasidList {
		var elements []string
		var inId, outId, iaString string
		switch i {
		case 0:
			elements = reFirst.FindStringSubmatch(iaidString)
			iaString = elements[1]
			outId = elements[2]
		case len(isdasidList) - 1:
			elements = reLast.FindStringSubmatch(iaidString)
			inId = elements[1]
			iaString = elements[2]
		default:
			elements = reIntermediate.FindStringSubmatch(iaidString)
			inId = elements[1]
			iaString = elements[2]
			outId = elements[3]
		}
		ia, err := addr.IAFromString(iaString)
		if err != nil {
			return err
		}
		if inId != "" {
			spd.IAList[index] = ia
			err = spd.IDList[index].UnmarshalText([]byte(inId))
			index++
		}
		if outId != "" {
			spd.IAList[index] = ia
			err = spd.IDList[index].UnmarshalText([]byte(outId))
			index++
		}
	}
	return nil
}

func (spd *scionPathDescription) String() string {
	var sb strings.Builder
	for i, ia := range spd.IAList {
		if i > 0 {
			sb.WriteString(",")
		}
		sb.WriteString(ia.String())
		sb.WriteString(" ")
		sb.WriteString(spd.IDList[i].String())
	}
	return sb.String()
}

func (spd *scionPathDescription) IsEqual(other *scionPathDescription) bool {
	if len(spd.IAList) != len(other.IAList) {
		return false
	}
	for i, isdas := range spd.IAList {
		if isdas != other.IAList[i] || spd.IDList[i] != other.IDList[i] {
			return false
		}
	}
	return true
}

func NewScionPathDescription(p snet.Path) *scionPathDescription {
	var spd scionPathDescription
	spd.IAList = make([]addr.IA, len(p.Interfaces()))
	spd.IDList = make([]common.IFIDType, len(p.Interfaces()))
	for i, ifs := range p.Interfaces() {
		spd.IAList[i] = ifs.IA()
		spd.IDList[i] = ifs.ID()
	}
	return &spd
}
