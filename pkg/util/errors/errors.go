package errors

import "strings"

import kapierrors "k8s.io/kubernetes/pkg/api/errors"

// TolerateNotFoundError tolerates 'not found' errors
func TolerateNotFoundError(err error) error {
	if kapierrors.IsNotFound(err) {
		return nil
	}
	return err
}

// ErrorToSentence will capitalize the first letter of the error
// message and add a period to the end if one is not present.
func ErrorToSentence(err error) string {
	msg := err.Error()
	if len(msg) == 0 {
		return msg
	}
	msg = strings.ToUpper(msg)[:1] + msg[1:]
	if !strings.HasSuffix(msg, ".") {
		msg = msg + "."
	}
	return msg
}